"""
뉴스 기사 클러스터링 모듈 (리팩토링 버전)

기능:
- 결측치(본문 내용이 없는 기사) 필터링
- OpenAI text-embedding-3-small 기반 텍스트(본문) 임베딩
- 코사인 유사도(Cosine Similarity) 기반 계층적 클러스터링
- 클러스터 내 유사도 검증 로그 (similarity_debug_log.json) 저장
- 대표 기사 추출 (클러스터 중 가장 긴 본문을 가진 기사)
"""

import os
import json
import logging
import numpy as np
from staging_manager import article_keywords

from briefing_candidates import (
    edition_window,
    publication_in_edition,
    validate_candidate_batch,
)

try:
    from supabase_uploader import upload_clustered_result_to_supabase
except ImportError:
    upload_clustered_result_to_supabase = None

# =====================================================================
# [.env 파일 자동 로드 - python-dotenv 없이 네이티브 지원]
# =====================================================================
def _load_env_if_exists():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip("'").strip('"')

_load_env_if_exists()

try:
    from openai import OpenAI
except ImportError:
    logging.warning("openai 패키지가 설치되지 않았습니다. 'pip install openai'를 실행하세요.")

try:
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.decomposition import PCA
except ImportError:
    logging.warning("scikit-learn 패키지가 설치되지 않았습니다. 'pip install scikit-learn'을 실행하세요.")

try:
    import matplotlib
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd

    # 폰트 깨짐 방지 (Mac: AppleGothic, Windows: Malgun Gothic)
    if os.name == 'posix':
        plt.rc('font', family='AppleGothic')
    else:
        plt.rc('font', family='Malgun Gothic')
    plt.rc('axes', unicode_minus=False)
except ImportError:
    logging.warning("시각화 라이브러리가 없습니다. 'pip install matplotlib seaborn pandas'를 실행하세요.")


# =====================================================================
# [환경 변수 & 글로벌 설정]
# 이 값을 조절하여 클러스터링의 타이트함을 결정합니다.
# 코사인 유사도 기준이므로 1.0에 가까울수록 아주 똑같은 기사만 묶입니다.
# 기존 0.8(너무 엄격)에서 0.6으로 기본값을 완화합니다.
# =====================================================================
SIMILARITY_THRESHOLD = 0.6
# AgglomerativeClustering의 distance는 (1 - 유사도) 로 계산되므로
DISTANCE_THRESHOLD = 1.0 - SIMILARITY_THRESHOLD


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def load_valid_articles(source: dict) -> list[dict]:
    """Normalize only the supplied edition snapshot, never scan cache files."""
    briefing_date = source.get("meta", {}).get("briefing_date")
    if not briefing_date:
        raise ValueError("Clustering input requires an explicit briefing_date")
    edition_window(briefing_date)
    if not source.get("articles"):
        raise ValueError(f"No source articles for edition {briefing_date}")
    articles = []
    for item in source["articles"]:
        title = str(item.get("title") or "").strip()
        content = str(
            item.get("fullText") or item.get("content") or ""
        ).strip()
        link = str(item.get("link") or item.get("url") or "").strip()
        published = item.get("pubDate") or item.get("pub_date") or ""
        if not title or not content or not link:
            continue
        if publication_in_edition(published, briefing_date):
            keywords = article_keywords(item) or ["기타"]
            articles.append({
                "keyword": keywords[0],
                "keywords": keywords,
                "title": title,
                "content": content,
                "link": link,
                "pubDate": published,
                "source": (
                    item.get("source_type") or item.get("source") or "unknown"
                ),
            })
    if not articles:
        raise ValueError(
            f"No valid source articles for edition {briefing_date}"
        )
    return articles


def get_embeddings(texts: list[str]) -> np.ndarray:
    """
    [2단계: 텍스트 임베딩]
    OpenAI API를 사용하여 텍스트 리스트를 벡터(숫자) 배열로 변환합니다.
    """
    if not texts:
        return np.array([])

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logging.error("환경 변수 'OPENAI_API_KEY'가 설정되어 있지 않습니다.")
        return np.array([])

    try:
        client = OpenAI(api_key=api_key)

        # OpenAI API는 한 번에 보낼 수 있는 토큰 한도(max 300,000 tokens)가 있음
        # 기사가 많을 경우 배칭(Batching) 처리하여 50개 단위로 끊어서 요청
        batch_size = 50
        all_embeddings = []

        import math
        total_batches = math.ceil(len(texts) / batch_size)

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            logging.info(f"임베딩 요청 중... (배치 {i//batch_size + 1}/{total_batches})")

            response = client.embeddings.create(
                input=batch_texts,
                model="text-embedding-3-small"
            )
            # 순서대로 리스트에 추가
            batch_embeddings = [data_obj.embedding for data_obj in response.data]
            all_embeddings.extend(batch_embeddings)

        return np.array(all_embeddings)

    except Exception as e:
        logging.error(f"OpenAI API 호출 중 오류 발생: {e}")
        return np.array([])


def debug_and_log_similarity(labels: np.ndarray, articles: list[dict], vectors: np.ndarray, cache_dir: str):
    """
    [3단계: 신규 추가⭐️ 디버깅 로그]
    클러스터별로 어떤 기사들이 묶였는지, 그리고 묶인 기사들 간의 "코사인 유사도"가 몇 점인지 추적하여 JSON 파일로 남깁니다.
    """
    debug_log = {
        "metadata": {
            "similarity_threshold": SIMILARITY_THRESHOLD,
            "distance_threshold": DISTANCE_THRESHOLD,
            "total_articles": len(articles),
            "total_clusters": len(set(labels))
        },
        "clusters": []
    }

    # 레이블별로 인덱스 그룹화
    cluster_indices = {}
    for idx, label in enumerate(labels):
        cluster_indices.setdefault(label, []).append(idx)

    for label, indices in cluster_indices.items():
        cluster_info = {
            "cluster_id": int(label),
            "article_count": len(indices),
            "articles": [{"title": articles[i]["title"]} for i in indices],
            "pairwise_similarities": []
        }

        # 클러스터 내 기사가 2개 이상일 때만 유사도 측정
        if len(indices) >= 2:
            # 해당 클러스터에 속한 벡터들 추출
            cluster_vectors = vectors[indices]
            # 벡터들끼리의 코사인 유사도 행렬 계산 (값의 범위: -1.0 ~ 1.0)
            sim_matrix = cosine_similarity(cluster_vectors)

            # 상삼각행렬(대각선 제외)을 돌면서 기사 A와 B의 유사도 기록
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    score = float(sim_matrix[i, j])
                    cluster_info["pairwise_similarities"].append({
                        "article_1": articles[indices[i]]["title"],
                        "article_2": articles[indices[j]]["title"],
                        "similarity_score": round(score, 4)
                    })

        debug_log["clusters"].append(cluster_info)

    # 콘솔 출력 (보기 좋게)
    logging.info(f"✅ 디버그: {len(articles)}개 기사가 {len(set(labels))}개의 클러스터로 묶였습니다.")

    # JSON 파일 저장
    debug_file_path = os.path.join(cache_dir, "similarity_debug_log.json")
    try:
        with open(debug_file_path, "w", encoding="utf-8") as f:
            json.dump(debug_log, f, ensure_ascii=False, indent=2)
        logging.info(f"✅ 상세 유사도 디버깅 로그를 저장했습니다: {debug_file_path}")
    except Exception as e:
        logging.error(f"디버깅 로그 저장 실패: {e}")


def visualize_clusters(labels: np.ndarray, articles: list[dict], vectors: np.ndarray, cache_dir: str):
    """
    [시각화] 클러스터링 결과를 3가지 그래프로 그려 파일로 저장합니다.
    """
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        from collections import Counter
    except ImportError:
        logging.warning("시각화 라이브러리가 없어 그래프 생성을 생략합니다.")
        return

    logging.info("시각화 그래프(3종)를 생성하고 저장합니다...")

    # 1. 클러스터별 기사 개수 바 차트 (Bar Chart)
    counts = Counter(labels)
    # 개수 기준 내림차순 정렬
    sorted_clusters = sorted(counts.items(), key=lambda x: x[1], reverse=True)

    cluster_ids = [f"Cluster {k}" for k, v in sorted_clusters]
    cluster_sizes = [v for k, v in sorted_clusters]

    plt.figure(figsize=(12, 6))
    sns.barplot(x=cluster_ids, y=cluster_sizes, hue=cluster_ids, palette="viridis", legend=False)
    plt.xticks(rotation=45, ha='right')
    plt.title("클러스터별 기사 분포 (이슈 크기)")
    plt.xlabel("클러스터 번호")
    plt.ylabel("기사 개수")
    plt.tight_layout()
    plt.savefig(os.path.join(cache_dir, "cluster_bar.png"), dpi=150)
    plt.close()

    # 2. 기사 간 코사인 유사도 분포 히스토그램 (Histogram)
    sim_matrix = cosine_similarity(vectors)
    # 상단 삼각행렬(대각선 제외)에서 유사도 값 추출 (전체 쌍)
    upper_indices = np.triu_indices_from(sim_matrix, k=1)
    pairwise_sims = sim_matrix[upper_indices]

    plt.figure(figsize=(10, 6))
    sns.histplot(pairwise_sims, bins=50, kde=True, color="skyblue")

    # 임계값(Threshold)에 빨간 점선 긋기
    plt.axvline(SIMILARITY_THRESHOLD, color='red', linestyle='--', linewidth=2,
                label=f'Threshold ({SIMILARITY_THRESHOLD})')

    plt.title("기사 간 코사인 유사도 분포")
    plt.xlabel("Cosine Similarity")
    plt.ylabel("빈도 (Frequency)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(cache_dir, "similarity_hist.png"), dpi=150)
    plt.close()

    # 3. 2D 군집화 산점도 (Scatter Plot with PCA)
    from sklearn.decomposition import PCA

    pca = PCA(n_components=2, random_state=42)
    vectors_2d = pca.fit_transform(vectors)

    plt.figure(figsize=(12, 8))

    # 고유 클러스터 개수 파악
    unique_labels = list(set(labels))
    palette = sns.color_palette("tab20", n_colors=len(unique_labels))

    sns.scatterplot(
        x=vectors_2d[:, 0],
        y=vectors_2d[:, 1],
        hue=labels,
        palette=palette,
        legend="full" if len(unique_labels) <= 20 else False,
        s=100,
        alpha=0.8,
        edgecolor='w'
    )
    plt.title("뉴스 임베딩 2D 군집화 지도 (PCA)")
    plt.xlabel("PCA Dimension 1")
    plt.ylabel("PCA Dimension 2")
    if len(unique_labels) <= 20:
        plt.legend(title="Cluster Label", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(cache_dir, "cluster_scatter.png"), dpi=150)
    plt.close()

    logging.info("그래프 3장 저장 완료: cluster_bar.png, similarity_hist.png, cluster_scatter.png")


def cluster_and_extract(articles: list[dict], cache_dir: str = "cache") -> list[dict]:
    """
    [4단계 & 5단계: 클러스터링 수행 및 대표 기사 추출]
    """
    # 1. 예외 방어 (기사가 1개 이하면 바로 반환)
    if len(articles) <= 1:
        logging.info("클러스터링을 위한 군집 정보가 부족합니다. 그대로 반환합니다.")
        return articles

    # 2. 이번에는 "본문(content)"만을 사용하여 임베딩
    texts_to_embed = [a["content"][:4000] for a in articles]
    logging.info(f"{len(texts_to_embed)}건의 기사에 대해 임베딩을 요청합니다...")

    vectors = get_embeddings(texts_to_embed)
    if len(vectors) != len(articles):
        raise RuntimeError("Clustering embeddings missing or incomplete")

    # 3. AgglomerativeClustering
    # 요구사항: metric='cosine', linkage='average', distance_threshold는 파라미터 적용
    logging.info(f"클러스터링 진행 중 (Threshold: {SIMILARITY_THRESHOLD*100}% 유사도 기준)...")
    try:
        model = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage="average",
            distance_threshold=DISTANCE_THRESHOLD
        )
        model.fit(vectors)
    except Exception as e:
        raise RuntimeError("Article clustering failed") from e

    labels = model.labels_

    # 4. 디버깅 및 유사도 확인 로직 호출 (신규 추가)
    debug_and_log_similarity(labels, articles, vectors, cache_dir)

    # 4-5. 시각화 그래프 저장 (신규 추가)
    visualize_clusters(labels, articles, vectors, cache_dir)

    # 5. 대표 기사 추출 (가장 본문이 긴 것)
    cluster_dict = {}
    for idx, label in enumerate(labels):
        cluster_dict.setdefault(label, []).append(articles[idx])

    representatives = []
    for cluster_id, cluster_group in cluster_dict.items():
        # content의 길이가 제일 긴 기사를 이 그룹의 대표로 선정!
        longest_article = max(cluster_group, key=lambda a: len(a["content"]))
        representatives.append(longest_article)

    return representatives


def run_pipeline(source: dict, cache_dir: str = "cache") -> dict:
    """Return fresh edition representatives, never read previous reports."""
    output_filename = "clustered_result.json"

    # 1. 데이터 로드 (결측치 제외)
    articles = load_valid_articles(source)
    os.makedirs(cache_dir, exist_ok=True)

    # Preserve each keyword's candidate pool when the same event matches several.
    by_keyword = {}
    for article in articles:
        for keyword in article["keywords"]:
            by_keyword.setdefault(keyword, []).append({
                **article, "keyword": keyword,
            })
    grouped_result = {}
    for keyword, keyword_articles in by_keyword.items():
        reps = cluster_and_extract(keyword_articles, cache_dir)
        if not reps:
            raise RuntimeError(
                f"No representatives returned for keyword={keyword}"
            )
        grouped_result[keyword] = reps

    batch = {
        "briefing_date": source["meta"]["briefing_date"],
        "status": "success",
        "candidate_source": "cluster_representatives",
        "source_count": len(articles),
        "articles": [
            {
                # URL is the source identity before a DB-generated ID exists.
                "id": rep["link"],
                "keyword": keyword,
                "title": rep["title"],
                "url": rep["link"],
                "content": rep["content"],
                "pub_date": rep["pubDate"],
                "source_type": rep["source"],
            }
            for keyword, reps in grouped_result.items()
            for rep in reps
        ],
    }
    validate_candidate_batch(batch, source["meta"]["briefing_date"])

    # 6. 최종 결과 저장
    out_path = os.path.join(cache_dir, output_filename)
    try:
        os.makedirs(cache_dir, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(grouped_result, f, ensure_ascii=False, indent=2)

        # 보기 좋게 요약 출력
        logging.info("🎉 최종 처리 완료: 주제별 대표 기사 요약")
        for k, v in grouped_result.items():
            logging.info(f"  - [{k}] {len(v)}건의 대표 기사")

        logging.info(f"저장 위치 -> {out_path}")
    except Exception as e:
        raise RuntimeError("Cluster report could not be saved") from e

    # Retain the existing optional DB report upload, but propagate failures.
    # Candidate selection does not query this table; the orchestrator also
    # uploads all raw articles, including non-representatives and full bodies.
    if upload_clustered_result_to_supabase is None:
        logging.warning("Clustered DB upload unavailable; using in-memory batch")
    else:
        upload_result = upload_clustered_result_to_supabase(grouped_result)
        logging.info("Clustered DB upload result: %s", upload_result)
    return batch


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Cluster an explicit edition snapshot"
    )
    parser.add_argument("input", help="JSON with meta.briefing_date and articles")
    args = parser.parse_args()
    with open(args.input, encoding="utf-8") as stream:
        run_pipeline(json.load(stream))
