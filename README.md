# news

Flutter 기반 Daily Briefing 앱입니다.

## Android 에뮬레이터 실행 가이드

### 1. 환경 확인
아래 명령으로 Flutter/Android SDK 상태를 먼저 확인합니다.

```powershell
flutter doctor -v
```

### 2. 에뮬레이터 목록 확인

```powershell
flutter emulators
```

### 3. 에뮬레이터 실행
`<emulator_id>`를 원하는 ID로 바꿔 실행합니다.

```powershell
flutter emulators --launch <emulator_id>
```

예시:

```powershell
flutter emulators --launch Pixel_9_ASCII
```

### 4. 디바이스 연결 확인
`device` 상태로 보여야 정상입니다.

```powershell
adb devices -l
flutter devices
```

### 5. 앱 실행
프로젝트 루트(`pubspec.yaml` 위치)에서 실행합니다.

```powershell
flutter pub get
flutter run -d emulator-5554
```

## 트러블슈팅

### `adb devices`에 `offline`으로 나오는 경우

```powershell
adb kill-server
adb start-server
Get-Process -Name emulator,qemu-system-x86_64,adb -ErrorAction SilentlyContinue | Stop-Process -Force
flutter emulators --launch <emulator_id>
adb devices -l
```

### Windows에서 Kotlin daemon 경로 오류가 나는 경우
사용자 경로 이슈가 있으면 Gradle 캐시 경로를 ASCII 경로로 지정한 뒤 실행합니다.

```powershell
$env:GRADLE_USER_HOME='C:\gradle-cache'
flutter run -d emulator-5554
```
