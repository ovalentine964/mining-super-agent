import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

/// ─────────────────────────────────────────────────────────────────────────────
/// Channel Manager — Multi-channel messaging bridge for Sovereign Resource DAO
///
/// Architecture:
///   Flutter App  ←──WebSocket──→  FastAPI Backend  ←──HTTP──→  Channel Bots
///       │                              │                         │
///       │  (native push / in-app)      │  (message routing)      │
///       ▼                              ▼                         ▼
///   Push Notifications          AI Agent Pipeline         Telegram / WhatsApp
///
/// The ChannelManager in the Flutter app:
///   1. Maintains a persistent WebSocket to the backend for real-time messages
///   2. Registers the user's linked channel accounts (Telegram, WhatsApp, etc.)
///   3. Receives routed messages from ANY channel and displays them in-app
///   4. Sends replies that the backend routes back to the originating channel
///   5. Manages channel-specific settings (mute, auto-translate, etc.)
/// ─────────────────────────────────────────────────────────────────────────────

// ── Enums & Models ──────────────────────────────────────────────────────────

enum ChannelType {
  telegram,
  whatsapp,
  discord,
  sms,
  inApp,
}

enum ChannelStatus {
  disconnected,
  connecting,
  connected,
  error,
}

enum MessageType {
  text,
  photo,
  video,
  audio,
  document,
  location,
  sticker,
  reaction,
}

class ChannelAccount {
  final ChannelType type;
  final String channelId;       // e.g. Telegram chat_id or WhatsApp phone number
  final String displayName;     // e.g. @username or contact name
  final String? avatarUrl;
  final ChannelStatus status;
  final DateTime? lastSeen;
  final Map<String, dynamic>? metadata;

  const ChannelAccount({
    required this.type,
    required this.channelId,
    required this.displayName,
    this.avatarUrl,
    this.status = ChannelStatus.disconnected,
    this.lastSeen,
    this.metadata,
  });

  ChannelAccount copyWith({
    ChannelStatus? status,
    DateTime? lastSeen,
    Map<String, dynamic>? metadata,
  }) {
    return ChannelAccount(
      type: type,
      channelId: channelId,
      displayName: displayName,
      avatarUrl: avatarUrl,
      status: status ?? this.status,
      lastSeen: lastSeen ?? this.lastSeen,
      metadata: metadata ?? this.metadata,
    );
  }

  Map<String, dynamic> toJson() => {
    'type': type.name,
    'channel_id': channelId,
    'display_name': displayName,
    'avatar_url': avatarUrl,
    'status': status.name,
    'last_seen': lastSeen?.toIso8601String(),
    'metadata': metadata,
  };

  factory ChannelAccount.fromJson(Map<String, dynamic> json) {
    return ChannelAccount(
      type: ChannelType.values.byName(json['type']),
      channelId: json['channel_id'],
      displayName: json['display_name'],
      avatarUrl: json['avatar_url'],
      status: ChannelStatus.values.byName(json['status'] ?? 'disconnected'),
      lastSeen: json['last_seen'] != null
          ? DateTime.parse(json['last_seen'])
          : null,
      metadata: json['metadata'],
    );
  }
}

class ChannelMessage {
  final String id;
  final ChannelType sourceChannel;
  final String senderId;
  final String senderName;
  final MessageType type;
  final String? text;
  final String? mediaUrl;        // URL to photo/video/audio/document
  final String? thumbnailUrl;
  final String? caption;
  final Map<String, dynamic>? location;  // {lat, lng}
  final DateTime timestamp;
  final bool isIncoming;
  final String? threadId;        // Groups messages in a conversation
  final Map<String, dynamic>? rawPayload;  // Original webhook payload

  const ChannelMessage({
    required this.id,
    required this.sourceChannel,
    required this.senderId,
    required this.senderName,
    required this.type,
    this.text,
    this.mediaUrl,
    this.thumbnailUrl,
    this.caption,
    this.location,
    required this.timestamp,
    required this.isIncoming,
    this.threadId,
    this.rawPayload,
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'source_channel': sourceChannel.name,
    'sender_id': senderId,
    'sender_name': senderName,
    'type': type.name,
    'text': text,
    'media_url': mediaUrl,
    'thumbnail_url': thumbnailUrl,
    'caption': caption,
    'location': location,
    'timestamp': timestamp.toIso8601String(),
    'is_incoming': isIncoming,
    'thread_id': threadId,
    'raw_payload': rawPayload,
  };

  factory ChannelMessage.fromJson(Map<String, dynamic> json) {
    return ChannelMessage(
      id: json['id'],
      sourceChannel: ChannelType.values.byName(json['source_channel']),
      senderId: json['sender_id'],
      senderName: json['sender_name'],
      type: MessageType.values.byName(json['type']),
      text: json['text'],
      mediaUrl: json['media_url'],
      thumbnailUrl: json['thumbnail_url'],
      caption: json['caption'],
      location: json['location'],
      timestamp: DateTime.parse(json['timestamp']),
      isIncoming: json['is_incoming'] ?? true,
      threadId: json['thread_id'],
      rawPayload: json['raw_payload'],
    );
  }
}

class ChannelConfig {
  final ChannelType type;
  final bool enabled;
  final bool muted;
  final bool autoTranslate;
  final String? targetLanguage;
  final bool receiveNotifications;
  final Map<String, dynamic>? customSettings;

  const ChannelConfig({
    required this.type,
    this.enabled = true,
    this.muted = false,
    this.autoTranslate = false,
    this.targetLanguage,
    this.receiveNotifications = true,
    this.customSettings,
  });

  ChannelConfig copyWith({
    bool? enabled,
    bool? muted,
    bool? autoTranslate,
    String? targetLanguage,
    bool? receiveNotifications,
    Map<String, dynamic>? customSettings,
  }) {
    return ChannelConfig(
      type: type,
      enabled: enabled ?? this.enabled,
      muted: muted ?? this.muted,
      autoTranslate: autoTranslate ?? this.autoTranslate,
      targetLanguage: targetLanguage ?? this.targetLanguage,
      receiveNotifications: receiveNotifications ?? this.receiveNotifications,
      customSettings: customSettings ?? this.customSettings,
    );
  }

  Map<String, dynamic> toJson() => {
    'type': type.name,
    'enabled': enabled,
    'muted': muted,
    'auto_translate': autoTranslate,
    'target_language': targetLanguage,
    'receive_notifications': receiveNotifications,
    'custom_settings': customSettings,
  };
}

// ── Channel Manager ─────────────────────────────────────────────────────────

/// Central service managing all messaging channel connections.
///
/// Usage:
/// ```dart
/// final manager = ChannelManager(baseUrl: 'https://api.sovereigndao.org');
/// await manager.initialize(authToken: userToken);
///
/// // Link a Telegram account
/// await manager.linkChannel(ChannelType.telegram, channelId: '123456789');
///
/// // Listen for messages from any channel
/// manager.messages.listen((msg) {
///   print('${msg.senderName}: ${msg.text ?? "[media]"}');
/// });
///
/// // Send a reply back through the same channel
/// await manager.sendMessage(
///   targetChannel: msg.sourceChannel,
///   targetId: msg.senderId,
///   text: 'Analysis complete: 85% forest cover detected.',
/// );
/// ```
class ChannelManager {
  final String baseUrl;
  WebSocketChannel? _wsChannel;
  StreamSubscription? _wsSubscription;
  String? _authToken;

  // ── State ────────────────────────────────────────────────────────────────
  final List<ChannelAccount> _linkedAccounts = [];
  final Map<ChannelType, ChannelConfig> _configs = {};
  final StreamController<ChannelMessage> _messageController =
      StreamController<ChannelMessage>.broadcast();
  final StreamController<ChannelStatus> _statusController =
      StreamController<ChannelStatus>.broadcast();
  final Map<String, List<ChannelMessage>> _threadHistory = {};

  // ── Public Streams ──────────────────────────────────────────────────────
  /// Stream of incoming messages from all linked channels.
  Stream<ChannelMessage> get messages => _messageController.stream;

  /// Stream of channel status changes.
  Stream<ChannelStatus> get statusChanges => _statusController.stream;

  /// Current linked accounts.
  List<ChannelAccount> get linkedAccounts => List.unmodifiable(_linkedAccounts);

  /// Current channel configs.
  Map<ChannelType, ChannelConfig> get configs => Map.unmodifiable(_configs);

  /// Whether the manager is connected to the backend.
  bool get isConnected => _wsChannel != null;

  ChannelManager({required this.baseUrl});

  // ── Lifecycle ───────────────────────────────────────────────────────────

  /// Initialize the channel manager and connect to the backend.
  Future<void> initialize({required String authToken}) async {
    _authToken = authToken;

    // Load linked accounts and configs from backend
    await _loadLinkedAccounts();
    await _loadChannelConfigs();

    // Establish WebSocket for real-time message routing
    await _connectWebSocket();

    // Fetch any messages missed while offline
    await _syncMissedMessages();
  }

  /// Clean up resources.
  Future<void> dispose() async {
    await _wsSubscription?.cancel();
    await _wsChannel?.sink.close();
    await _messageController.close();
    await _statusController.close();
  }

  // ── Channel Linking ─────────────────────────────────────────────────────

  /// Link a messaging channel to the current user account.
  ///
  /// For Telegram: the user starts the bot and sends /link <code>,
  ///   the backend verifies and stores the chat_id mapping.
  /// For WhatsApp: the user sends a verification code to the Business number.
  Future<ChannelAccount> linkChannel(
    ChannelType type, {
    required String channelId,
    String? displayName,
    Map<String, dynamic>? metadata,
  }) async {
    final response = await _authenticatedPost('/channels/link', body: {
      'channel_type': type.name,
      'channel_id': channelId,
      'display_name': displayName,
      'metadata': metadata,
    });

    final account = ChannelAccount.fromJson(response);
    _linkedAccounts.add(account);
    return account;
  }

  /// Unlink a messaging channel.
  Future<void> unlinkChannel(ChannelType type, String channelId) async {
    await _authenticatedPost('/channels/unlink', body: {
      'channel_type': type.name,
      'channel_id': channelId,
    });
    _linkedAccounts.removeWhere(
      (a) => a.type == type && a.channelId == channelId,
    );
  }

  /// Generate a linking code for Telegram.
  /// User starts @SovereignDAO_bot and sends: /link CODE123
  Future<String> generateTelegramLinkCode() async {
    final response = await _authenticatedPost('/channels/telegram/link-code');
    return response['code']; // e.g. "ABCD-1234"
  }

  /// Generate a linking code for WhatsApp.
  /// User sends the code as a WhatsApp message to the Business number.
  Future<String> generateWhatsAppLinkCode() async {
    final response = await _authenticatedPost('/channels/whatsapp/link-code');
    return response['code'];
  }

  // ── Sending Messages ────────────────────────────────────────────────────

  /// Send a message through a specific channel.
  ///
  /// The backend routes the message to the appropriate bot:
  ///   - Telegram: calls Bot API sendMessage / sendPhoto / etc.
  ///   - WhatsApp: calls Meta Cloud API messages endpoint
  Future<ChannelMessage> sendMessage({
    required ChannelType targetChannel,
    required String targetId,
    String? text,
    String? mediaUrl,
    String? caption,
    MessageType type = MessageType.text,
    Map<String, dynamic>? location,
    String? threadId,
  }) async {
    final response = await _authenticatedPost('/channels/send', body: {
      'target_channel': targetChannel.name,
      'target_id': targetId,
      'type': type.name,
      'text': text,
      'media_url': mediaUrl,
      'caption': caption,
      'location': location,
      'thread_id': threadId,
    });

    final message = ChannelMessage.fromJson(response);
    return message;
  }

  /// Reply to a specific message (routes back through originating channel).
  Future<ChannelMessage> replyToMessage({
    required ChannelMessage original,
    String? text,
    String? mediaUrl,
    String? caption,
    MessageType type = MessageType.text,
  }) async {
    return sendMessage(
      targetChannel: original.sourceChannel,
      targetId: original.senderId,
      text: text,
      mediaUrl: mediaUrl,
      caption: caption,
      type: type,
      threadId: original.threadId,
    );
  }

  /// Broadcast a message to all linked channels of a given type.
  Future<List<ChannelMessage>> broadcastMessage({
    required ChannelType channel,
    required String text,
    MessageType type = MessageType.text,
  }) async {
    final targets = _linkedAccounts.where((a) => a.type == channel);
    final results = <ChannelMessage>[];
    for (final account in targets) {
      final msg = await sendMessage(
        targetChannel: channel,
        targetId: account.channelId,
        text: text,
        type: type,
      );
      results.add(msg);
    }
    return results;
  }

  // ── Channel Configuration ───────────────────────────────────────────────

  /// Update configuration for a channel type.
  Future<void> updateChannelConfig(ChannelConfig config) async {
    await _authenticatedPost('/channels/config', body: config.toJson());
    _configs[config.type] = config;
  }

  /// Get the thread history for a conversation.
  List<ChannelMessage> getThreadHistory(String threadId) {
    return List.unmodifiable(_threadHistory[threadId] ?? []);
  }

  // ── Internal: WebSocket Connection ──────────────────────────────────────

  Future<void> _connectWebSocket() async {
    final wsUrl = baseUrl.replaceFirst('http', 'ws');
    _wsChannel = WebSocketChannel.connect(
      Uri.parse('$wsUrl/ws/channels?token=$_authToken'),
    );

    _wsSubscription = _wsChannel!.stream.listen(
      (data) {
        try {
          final json = jsonDecode(data as String) as Map<String, dynamic>;
          _handleWebSocketMessage(json);
        } catch (e) {
          // Malformed message, log and continue
          print('[ChannelManager] WebSocket parse error: $e');
        }
      },
      onError: (error) {
        _statusController.add(ChannelStatus.error);
        _scheduleReconnect();
      },
      onDone: () {
        _statusController.add(ChannelStatus.disconnected);
        _scheduleReconnect();
      },
    );

    _statusController.add(ChannelStatus.connected);
  }

  void _handleWebSocketMessage(Map<String, dynamic> json) {
    final event = json['event'] as String?;

    switch (event) {
      case 'message':
        final message = ChannelMessage.fromJson(json['data']);
        _messageController.add(message);
        _addToThread(message);
        break;

      case 'status':
        final channelType = ChannelType.values.byName(json['data']['channel']);
        final status = ChannelStatus.values.byName(json['data']['status']);
        _updateAccountStatus(channelType, json['data']['channel_id'], status);
        break;

      case 'typing':
        // Forward typing indicators if needed
        break;

      case 'delivery_receipt':
        // Handle delivery confirmations
        break;

      default:
        print('[ChannelManager] Unknown WS event: $event');
    }
  }

  void _addToThread(ChannelMessage message) {
    final threadId = message.threadId ?? message.id;
    _threadHistory.putIfAbsent(threadId, () => []);
    _threadHistory[threadId]!.add(message);

    // Cap thread history at 500 messages
    if (_threadHistory[threadId]!.length > 500) {
      _threadHistory[threadId] = _threadHistory[threadId]!.sublist(
        _threadHistory[threadId]!.length - 500,
      );
    }
  }

  void _updateAccountStatus(
    ChannelType type,
    String channelId,
    ChannelStatus status,
  ) {
    final idx = _linkedAccounts.indexWhere(
      (a) => a.type == type && a.channelId == channelId,
    );
    if (idx >= 0) {
      _linkedAccounts[idx] = _linkedAccounts[idx].copyWith(
        status: status,
        lastSeen: DateTime.now(),
      );
    }
    _statusController.add(status);
  }

  Timer? _reconnectTimer;
  int _reconnectAttempts = 0;

  void _scheduleReconnect() {
    _reconnectAttempts++;
    final delay = Duration(
      seconds: (_reconnectAttempts * 2).clamp(2, 60),
    );
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(delay, () {
      _connectWebSocket();
    });
  }

  // ── Internal: HTTP Helpers ──────────────────────────────────────────────

  Future<void> _loadLinkedAccounts() async {
    final response = await _authenticatedGet('/channels/accounts');
    _linkedAccounts.clear();
    for (final json in (response['accounts'] as List)) {
      _linkedAccounts.add(ChannelAccount.fromJson(json));
    }
  }

  Future<void> _loadChannelConfigs() async {
    final response = await _authenticatedGet('/channels/configs');
    for (final entry in (response['configs'] as Map<String, dynamic>).entries) {
      final type = ChannelType.values.byName(entry.key);
      _configs[type] = ChannelConfig(
        type: type,
        enabled: entry.value['enabled'] ?? true,
        muted: entry.value['muted'] ?? false,
        autoTranslate: entry.value['auto_translate'] ?? false,
        targetLanguage: entry.value['target_language'],
        receiveNotifications: entry.value['receive_notifications'] ?? true,
        customSettings: entry.value['custom_settings'],
      );
    }
  }

  Future<void> _syncMissedMessages() async {
    final response = await _authenticatedGet('/channels/messages/sync');
    for (final json in (response['messages'] as List)) {
      final message = ChannelMessage.fromJson(json);
      _messageController.add(message);
      _addToThread(message);
    }
  }

  Future<Map<String, dynamic>> _authenticatedGet(String path) async {
    final uri = Uri.parse('$baseUrl/api/v1$path');
    final response = await http.get(uri, headers: _headers());
    _checkResponse(response);
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> _authenticatedPost(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1$path');
    final response = await http.post(
      uri,
      headers: _headers(),
      body: body != null ? jsonEncode(body) : null,
    );
    _checkResponse(response);
    return jsonDecode(response.body);
  }

  Map<String, String> _headers() => {
    'Content-Type': 'application/json',
    if (_authToken != null) 'Authorization': 'Bearer $_authToken',
  };

  void _checkResponse(http.Response response) {
    if (response.statusCode >= 400) {
      throw ChannelException(
        'HTTP ${response.statusCode}: ${response.body}',
        statusCode: response.statusCode,
      );
    }
  }
}

// ── Exceptions ──────────────────────────────────────────────────────────────

class ChannelException implements Exception {
  final String message;
  final int? statusCode;

  const ChannelException(this.message, {this.statusCode});

  @override
  String toString() => 'ChannelException($statusCode): $message';
}
