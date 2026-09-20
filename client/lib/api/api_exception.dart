/// Error raised for a non-2xx API response, parsed from the standard envelope
/// `{"error": {"code", "message", "request_id"}}` (§75).
class ApiException implements Exception {
  const ApiException(this.statusCode, this.code, this.message, {this.requestId});

  final int statusCode;
  final String code;
  final String message;
  final String? requestId;

  bool get isAuthError => statusCode == 401;

  @override
  String toString() => 'ApiException($statusCode, $code): $message';
}
