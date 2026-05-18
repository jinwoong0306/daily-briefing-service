import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SessionStore {
  const SessionStore._();

  static const FlutterSecureStorage _storage = FlutterSecureStorage();
  static const String _tokenKey = 'access_token';
  static String? accessToken;

  static bool get isAuthenticated =>
      accessToken != null && accessToken!.isNotEmpty;

  static Future<void> initialize() async {
    accessToken = await _storage.read(key: _tokenKey);
  }

  static Future<void> setAccessToken(String token) async {
    accessToken = token;
    await _storage.write(key: _tokenKey, value: token);
  }

  static Future<void> clear() async {
    accessToken = null;
    await _storage.delete(key: _tokenKey);
  }
}
