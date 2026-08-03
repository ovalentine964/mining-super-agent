import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:record/record.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import '../services/api_client.dart';
import '../services/voice_service.dart';
import '../services/on_device_voice.dart';

/// NVIDIA API key from compile-time define.
/// Pass via: flutter run --dart-define=NVIDIA_API_KEY=your_key
const _nvidiaApiKey = String.fromEnvironment( 'NVIDIA_API_KEY', defaultValue: '');

/// Interactive Voice Chat — Talk to the AI like a person
///
/// NOT push-to-talk. This is continuous voice conversation:
/// - User speaks naturally
/// - AI listens, transcribes, responds with voice
/// - Conversation flows like talking to a person
/// - Works online (NVIDIA NIM cloud) and offline (on-device)
class VoiceChatScreen extends StatefulWidget {
  const VoiceChatScreen({super.key});

  @override
  State<VoiceChatScreen> createState() => _VoiceChatScreenState();
}

class _VoiceChatScreenState extends State<VoiceChatScreen>
    with TickerProviderStateMixin {
  final _apiClient = ApiClient();
  final _audioRecorder = AudioRecorder();
  final _audioPlayer = AudioPlayer();

  // Voice services: on-device (offline) + cloud (NVIDIA NIM)
  late VoiceService _cloudVoiceService;
  final OnDeviceVoiceService _onDeviceVoice = OnDeviceVoiceService();
  bool _onDeviceAvailable = false;

  // Conversation state
  final _messages = <Map<String, dynamic>>[];
  String _selectedAgent = 'sentinel';

  // Voice state
  bool _listening = false;
  bool _processing = false;
  bool _speaking = false;
  bool _continuousMode = true; // Keep listening after each exchange
  String _currentTranscript = '';
  String _aiResponse = '';

  // Animation
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  final _agents = {
    'sentinel': {'name': 'Sentinel', 'emoji': '🛰️', 'desc': 'Ufuatiliaji wa setelaiti'},
    'auditor': {'name': 'Auditor', 'emoji': '💰', 'desc': 'Akili za fedha'},
    'advocate': {'name': 'Advocate', 'emoji': '⚖️', 'desc': 'Ulinzi wa kisheria'},
    'oracle': {'name': 'Oracle', 'emoji': '📊', 'desc': 'Akili za soko'},
    'ambassador': {'name': 'Ambassador', 'emoji': '🗣️', 'desc': 'Mawasiliano ya jamii'},
  };

  @override
  void initState() {
    super.initState();
    _cloudVoiceService = VoiceService(
      nvidiaApiKey: _nvidiaApiKey,
    );

    // Pulse animation for listening indicator
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 1),
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 0.8, end: 1.2).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _initAsync();
  }

  Future<void> _initAsync() async {
    // Try to initialize on-device model
    _onDeviceAvailable = await _onDeviceVoice.initialize();
    _initVoice();
  }

  Future<void> _initVoice() async {
    await Permission.microphone.request();
    // Start listening immediately
    _startListening();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _audioRecorder.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF1A1A2E),
      appBar: AppBar(
        title: Text('${_agents[_selectedAgent]!['emoji']} ${_agents[_selectedAgent]!['name']}'),
        backgroundColor: const Color(0xFF16213E),
        actions: [
          // Agent selector
          PopupMenuButton<String>(
            icon: const Icon(Icons.swap_horiz, color: Colors.white),
            onSelected: (v) => setState(() { _selectedAgent = v; }),
            itemBuilder: (_) => _agents.entries.map((e) => PopupMenuItem(
              value: e.key,
              child: ListTile(
                leading: Text(e.value['emoji']!, style: const TextStyle(fontSize: 24)),
                title: Text(e.value['name']!),
                subtitle: Text(e.value['desc']!),
              ),
            )).toList(),
          ),
          // Continuous mode toggle
          IconButton(
            icon: Icon(
              _continuousMode ? Icons.loop : Icons.loop_outlined,
              color: _continuousMode ? Colors.green : Colors.grey,
            ),
            tooltip: _continuousMode
                ? 'Continuous mode ON (keeps listening)'
                : 'Continuous mode OFF (manual)',
            onPressed: () => setState(() { _continuousMode = !_continuousMode; }),
          ),
        ],
      ),
      body: Column(
        children: [
          // Voice visualization area
          Expanded(
            flex: 3,
            child: Container(
              width: double.infinity,
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Color(0xFF16213E), Color(0xFF1A1A2E)],
                ),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // AI avatar with pulse
                  AnimatedBuilder(
                    animation: _pulseAnimation,
                    builder: (context, child) {
                      return Transform.scale(
                        scale: _listening ? _pulseAnimation.value : 1.0,
                        child: Container(
                          width: 120,
                          height: 120,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: _listening
                                ? Colors.green.withOpacity(0.3)
                                : _processing
                                    ? Colors.amber.withOpacity(0.3)
                                    : _speaking
                                        ? Colors.blue.withOpacity(0.3)
                                        : Colors.grey.withOpacity(0.2),
                            border: Border.all(
                              color: _listening
                                  ? Colors.green
                                  : _processing
                                      ? Colors.amber
                                      : _speaking
                                          ? Colors.blue
                                          : Colors.grey,
                              width: 3,
                            ),
                          ),
                          child: Center(
                            child: Text(
                              _agents[_selectedAgent]!['emoji']!,
                              style: const TextStyle(fontSize: 48),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                  const SizedBox(height: 24),

                  // Status text
                  Text(
                    _listening
                        ? 'Sikiliza... (Listening...)'
                        : _processing
                            ? 'Inafikiri... (Thinking...)'
                            : _speaking
                                ? 'Inazungumza... (Speaking...)'
                                : 'Gusa kuongea (Tap to speak)',
                    style: TextStyle(
                      color: _listening
                          ? Colors.green
                          : _processing
                              ? Colors.amber
                              : _speaking
                                  ? Colors.blue
                                  : Colors.white70,
                      fontSize: 18,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Current transcript
                  if (_currentTranscript.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 32),
                      child: Text(
                        _currentTranscript,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.white, fontSize: 16),
                      ),
                    ),

                  // AI response text
                  if (_aiResponse.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 8),
                      child: Text(
                        _aiResponse,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.amber, fontSize: 14),
                      ),
                    ),
                ],
              ),
            ),
          ),

          // Conversation history (scrollable)
          Expanded(
            flex: 2,
            child: Container(
              color: const Color(0xFF1A1A2E),
              child: ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: _messages.length,
                itemBuilder: (_, i) => _buildMessage(_messages[i]),
              ),
            ),
          ),

          // Voice control area
          Container(
            padding: const EdgeInsets.all(24),
            decoration: const BoxDecoration(
              color: Color(0xFF16213E),
              borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                // Stop/Start button
                _voiceButton(
                  icon: _listening ? Icons.stop : Icons.mic,
                  color: _listening ? Colors.red : Colors.green,
                  label: _listening ? 'Simama' : 'Ongea',
                  onTap: _listening ? _stopListening : _startListening,
                ),

                // Main talk button (hold to talk)
                GestureDetector(
                  onLongPressStart: (_) => _startListening(),
                  onLongPressEnd: (_) {
                    if (!_continuousMode) _stopListening();
                  },
                  child: Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _listening ? Colors.red : const Color(0xFF8B6914),
                      boxShadow: [
                        BoxShadow(
                          color: (_listening ? Colors.red : const Color(0xFF8B6914))
                              .withOpacity(0.4),
                          blurRadius: 20,
                          spreadRadius: _listening ? 8 : 2,
                        ),
                      ],
                    ),
                    child: Icon(
                      _listening ? Icons.mic : Icons.mic_none,
                      color: Colors.white,
                      size: 36,
                    ),
                  ),
                ),

                // Clear button
                _voiceButton(
                  icon: Icons.clear_all,
                  color: Colors.grey,
                  label: 'Futa',
                  onTap: _clearConversation,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _voiceButton({
    required IconData icon,
    required Color color,
    required String label,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: color, size: 32),
          const SizedBox(height: 4),
          Text(label, style: TextStyle(color: color, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _buildMessage(Map<String, dynamic> msg) {
    final isUser = msg['role'] == 'user';
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser)
            Text(
              _agents[_selectedAgent]!['emoji']!,
              style: const TextStyle(fontSize: 20),
            ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment:
                  isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                Text(
                  msg['content'] ?? '',
                  style: TextStyle(
                    color: isUser ? Colors.green : Colors.white,
                    fontSize: 14,
                  ),
                ),
                if (msg['time'] != null)
                  Text(
                    msg['time'],
                    style: const TextStyle(color: Colors.grey, fontSize: 10),
                  ),
              ],
            ),
          ),
          if (isUser) ...[
            const SizedBox(width: 8),
            const Icon(Icons.person, color: Colors.green, size: 20),
          ],
        ],
      ),
    );
  }

  // ── VOICE FLOW ────────────────────────────────────────────────────────────

  Future<void> _startListening() async {
    try {
      if (await _audioRecorder.hasPermission()) {
        final dir = await getTemporaryDirectory();
        final path = '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}.m4a';

        await _audioRecorder.start(
          const RecordConfig(encoder: AudioEncoder.aacLc),
          path: path,
        );

        setState(() {
          _listening = true;
          _currentTranscript = '';
          _aiResponse = '';
        });
      }
    } catch (e) {
      debugPrint('Start listening error: $e');
    }
  }

  Future<void> _stopListening() async {
    try {
      final path = await _audioRecorder.stop();
      setState(() { _listening = false; });

      if (path != null && File(path).existsSync()) {
        setState(() { _processing = true; });

        // Step 1: Transcribe — on-device first, cloud fallback
        String transcript;
        if (_onDeviceAvailable) {
          transcript = await _onDeviceVoice.transcribe(path);
        } else {
          transcript = await _cloudVoiceService.transcribe(path);
        }
        setState(() {
          _currentTranscript = transcript;
          _messages.add({
            'role': 'user',
            'content': transcript,
            'time': _currentTime(),
          });
        });

        // Step 2: Get AI response
        final result = await _apiClient.post('/agents/$_selectedAgent/chat', {
          'message': transcript,
        });
        final responseText = result['response'] ?? 'Sijaelewa.';

        setState(() {
          _aiResponse = responseText;
          _messages.add({
            'role': 'assistant',
            'content': responseText,
            'time': _currentTime(),
          });
          _processing = false;
          _speaking = true;
        });

        // Step 3: Speak response (NVIDIA NIM TTS)
        try {
          final audioBytes = await _voiceService.synthesize(responseText);
          final dir = await getTemporaryDirectory();
          final audioPath = '${dir.path}/response_${DateTime.now().millisecondsSinceEpoch}.mp3';
          await File(audioPath).writeAsBytes(audioBytes);

          await _audioPlayer.play(DeviceFileSource(audioPath));
          _audioPlayer.onPlayerComplete.listen((_) {
            setState(() { _speaking = false; });

            // Step 4: If continuous mode, start listening again
            if (_continuousMode && mounted) {
              Future.delayed(const Duration(milliseconds: 500), () {
                if (mounted) _startListening();
              });
            }
          });
        } catch (e) {
          setState(() { _speaking = false; });
          // If TTS fails, still continue listening
          if (_continuousMode && mounted) {
            Future.delayed(const Duration(milliseconds: 500), () {
              if (mounted) _startListening();
            });
          }
        }
      }
    } catch (e) {
      setState(() {
        _listening = false;
        _processing = false;
        _speaking = false;
      });
      debugPrint('Stop listening error: $e');
    }
  }

  void _clearConversation() {
    setState(() {
      _messages.clear();
      _currentTranscript = '';
      _aiResponse = '';
    });
  }

  String _currentTime() {
    final now = DateTime.now();
    return '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
  }
}
