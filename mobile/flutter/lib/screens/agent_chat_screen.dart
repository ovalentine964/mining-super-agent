import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:record/record.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import '../services/api_client.dart';
import '../services/voice_service.dart';

/// NVIDIA API key from compile-time define.
/// Pass via: flutter run --dart-define=NVIDIA_API_KEY=your_key
const _nvidiaApiKey = String.fromEnvironment( 'NVIDIA_API_KEY', defaultValue: '');

/// Agent Chat Screen — Talk to the five sovereign agents
/// Supports TEXT and VOICE input (record → transcribe → respond)
class AgentChatScreen extends StatefulWidget {
  const AgentChatScreen({super.key});

  @override
  State<AgentChatScreen> createState() => _AgentChatScreenState();
}

class _AgentChatScreenState extends State<AgentChatScreen> {
  final _apiClient = ApiClient();
  final _messageController = TextEditingController();
  final _messages = <Map<String, dynamic>>[];
  final _audioRecorder = AudioRecorder();
  final _audioPlayer = AudioPlayer();

  String _selectedAgent = 'sentinel';
  bool _loading = false;
  bool _recording = false;
  bool _playingAudio = false;
  String? _recordingPath;

  // Voice service (NVIDIA NIM cloud)
  late VoiceService _voiceService;

  final _agents = {
    'sentinel': {'name': 'Sentinel', 'emoji': '🛰️', 'desc': '24/7 satellite monitoring', 'desc_sw': 'Ufuatiliaji wa setelaiti'},
    'auditor': {'name': 'Auditor', 'emoji': '💰', 'desc': 'Financial intelligence', 'desc_sw': 'Akili za fedha'},
    'advocate': {'name': 'Advocate', 'emoji': '⚖️', 'desc': 'Legal defense', 'desc_sw': 'Ulinzi wa kisheria'},
    'oracle': {'name': 'Oracle', 'emoji': '📊', 'desc': 'Market intelligence', 'desc_sw': 'Akili za soko'},
    'ambassador': {'name': 'Ambassador', 'emoji': '🗣️', 'desc': 'Community communication', 'desc_sw': 'Mawasiliano ya jamii'},
  };

  @override
  void initState() {
    super.initState();
    // Initialize with env var or default — user sets in settings
    _voiceService = VoiceService(nvidiaApiKey: _nvidiaApiKey);
    _initRecorder();
  }

  Future<void> _initRecorder() async {
    final status = await Permission.microphone.request();
    if (status != PermissionStatus.granted) {
      debugPrint('Microphone permission denied');
    }
  }

  @override
  void dispose() {
    _audioRecorder.dispose();
    _audioPlayer.dispose();
    _messageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('${_agents[_selectedAgent]!['emoji']} ${_agents[_selectedAgent]!['name']}'),
        backgroundColor: const Color(0xFF8B6914),
        actions: [
          // Agent selector
          PopupMenuButton<String>(
            icon: const Icon(Icons.swap_horiz),
            tooltip: 'Badilisha Agent (Switch Agent)',
            onSelected: (v) => setState(() { _selectedAgent = v; }),
            itemBuilder: (_) => _agents.entries.map((e) => PopupMenuItem(
              value: e.key,
              child: ListTile(
                leading: Text(e.value['emoji']!, style: const TextStyle(fontSize: 24)),
                title: Text(e.value['name']!),
                subtitle: Text(e.value['desc_sw']!),
              ),
            )).toList(),
          ),
          // Voice settings
          IconButton(
            icon: const Icon(Icons.settings_voice),
            tooltip: 'Mipangilio ya Sauti (Voice Settings)',
            onPressed: _showVoiceSettings,
          ),
        ],
      ),
      body: Column(
        children: [
          // Agent info bar
          Container(
            padding: const EdgeInsets.all(12),
            color: const Color(0xFFF5F0E0),
            child: Row(
              children: [
                Text(_agents[_selectedAgent]!['emoji']!, style: const TextStyle(fontSize: 32)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _agents[_selectedAgent]!['name']!,
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      Text(
                        '${_agents[_selectedAgent]!['desc_sw']} — ${_agents[_selectedAgent]!['desc']}',
                        style: const TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                    ],
                  ),
                ),
                // Voice indicator
                if (_recording)
                  const Row(
                    children: [
                      Icon(Icons.mic, color: Colors.red, size: 20),
                      SizedBox(width: 4),
                      Text('Inarekodi...', style: TextStyle(color: Colors.red, fontSize: 12)),
                    ],
                  ),
              ],
            ),
          ),

          // Messages
          Expanded(
            child: _messages.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.chat_bubble_outline, size: 64, color: Colors.grey),
                        const SizedBox(height: 16),
                        const Text('Andika ujumbe au ongea', style: TextStyle(color: Colors.grey, fontSize: 16)),
                        const Text('Type or speak your message', style: TextStyle(color: Colors.grey, fontSize: 12)),
                        const SizedBox(height: 24),
                        // Quick actions
                        Wrap(
                          spacing: 8,
                          children: [
                            _quickAction('📸 Tuma Picha', 'Send a photo to identify minerals'),
                            _quickAction('💰 Bei za Soko', 'Get current market prices'),
                            _quickAction('⚖️ Hakiki Ofa', 'Check if a mining offer is fair'),
                            _quickAction('🛰️ Hali ya Ardhi', 'Check land status'),
                          ],
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _messages.length,
                    itemBuilder: (_, i) => _buildMessage(_messages[i]),
                  ),
          ),

          // Input area (text + voice)
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [BoxShadow(color: Colors.grey.shade300, blurRadius: 4)],
            ),
            child: Row(
              children: [
                // Voice button (hold to record)
                GestureDetector(
                  onLongPressStart: (_) => _startRecording(),
                  onLongPressEnd: (_) => _stopRecordingAndSend(),
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: _recording ? Colors.red : const Color(0xFF8B6914),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      _recording ? Icons.mic : Icons.mic_none,
                      color: Colors.white,
                      size: 28,
                    ),
                  ),
                ),
                const SizedBox(width: 8),

                // Text input
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: InputDecoration(
                      hintText: 'Andika hapa... (Type here)',
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(24)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      suffixIcon: IconButton(
                        icon: const Icon(Icons.camera_alt, color: Color(0xFF8B6914)),
                        tooltip: 'Tuma Picha (Send Photo)',
                        onPressed: _pickAndSendPhoto,
                      ),
                    ),
                    onSubmitted: (_) => _sendTextMessage(),
                  ),
                ),
                const SizedBox(width: 8),

                // Send button
                CircleAvatar(
                  backgroundColor: const Color(0xFF8B6914),
                  child: IconButton(
                    icon: _loading
                        ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : const Icon(Icons.send, color: Colors.white),
                    onPressed: _loading ? null : _sendTextMessage,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _quickAction(String label, String desc) {
    return ActionChip(
      avatar: const Icon(Icons.touch_app, size: 16),
      label: Text(label, style: const TextStyle(fontSize: 12)),
      onPressed: () {
        _messageController.text = label.split(' ').skip(1).join(' ');
        _sendTextMessage();
      },
    );
  }

  Widget _buildMessage(Map<String, dynamic> msg) {
    final isUser = msg['role'] == 'user';
    final hasAudio = msg['audio_path'] != null;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.78),
        decoration: BoxDecoration(
          color: isUser ? const Color(0xFF8B6914) : Colors.grey.shade100,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 4)],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Voice indicator for voice messages
            if (msg['is_voice'] == true)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.mic, size: 14, color: isUser ? Colors.white70 : Colors.grey),
                    const SizedBox(width: 4),
                    Text(
                      'Ujumbe wa Sauti (Voice)',
                      style: TextStyle(fontSize: 10, color: isUser ? Colors.white70 : Colors.grey),
                    ),
                  ],
                ),
              ),
            // Message text
            Text(
              msg['content'] ?? '',
              style: TextStyle(
                color: isUser ? Colors.white : Colors.black87,
                fontSize: 15,
              ),
            ),
            // Play audio button for voice responses
            if (hasAudio)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: IconButton(
                  icon: Icon(
                    _playingAudio ? Icons.stop_circle : Icons.play_circle_filled,
                    color: isUser ? Colors.white : const Color(0xFF8B6914),
                    size: 32,
                  ),
                  onPressed: () => _playAudio(msg['audio_path']),
                ),
              ),
            // Timestamp
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                msg['time'] ?? '',
                style: TextStyle(fontSize: 10, color: isUser ? Colors.white54 : Colors.grey),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ── TEXT MESSAGE ──────────────────────────────────────────────────────────

  Future<void> _sendTextMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _messages.add({
        'role': 'user',
        'content': text,
        'time': _currentTime(),
      });
      _loading = true;
    });
    _messageController.clear();

    try {
      final result = await _apiClient.post('/agents/$_selectedAgent/chat', {'message': text});
      setState(() {
        _messages.add({
          'role': 'assistant',
          'content': result['response'] ?? result['note'] ?? 'No response',
          'time': _currentTime(),
        });
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _messages.add({
          'role': 'assistant',
          'content': 'Hitilafu: $e\nError: $e',
          'time': _currentTime(),
        });
        _loading = false;
      });
    }
  }

  // ── VOICE MESSAGE ─────────────────────────────────────────────────────────

  Future<void> _startRecording() async {
    try {
      if (await _audioRecorder.hasPermission()) {
        final dir = await getTemporaryDirectory();
        final path = '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}.m4a';

        await _audioRecorder.start(
          const RecordConfig(encoder: AudioEncoder.aacLc),
          path: path,
        );

        setState(() {
          _recording = true;
          _recordingPath = path;
        });
      }
    } catch (e) {
      debugPrint('Recording error: $e');
    }
  }

  Future<void> _stopRecordingAndSend() async {
    try {
      final path = await _audioRecorder.stop();

      if (path != null && File(path).existsSync()) {
        // Add user voice message
        setState(() {
          _recording = false;
          _messages.add({
            'role': 'user',
            'content': '🎤 Ujumbe wa sauti...',
            'is_voice': true,
            'audio_path': path,
            'time': _currentTime(),
          });
          _loading = true;
        });

        try {
          // Step 1: Transcribe using NVIDIA NIM Whisper
          final transcription = await _voiceService.transcribe(path);

          // Update user message with transcription
          setState(() {
            _messages.last['content'] = '🎤 $transcription';
          });

          // Step 2: Send transcribed text to agent
          final result = await _apiClient.post('/agents/$_selectedAgent/chat', {
            'message': transcription,
          });

          final responseText = result['response'] ?? result['note'] ?? 'No response';

          // Step 3: Generate voice response using NVIDIA NIM TTS
          String? audioPath;
          try {
            final audioBytes = await _voiceService.synthesize(responseText);
            final dir = await getTemporaryDirectory();
            audioPath = '${dir.path}/response_${DateTime.now().millisecondsSinceEpoch}.mp3';
            await File(audioPath).writeAsBytes(audioBytes);
          } catch (e) {
            debugPrint('TTS failed (text response only): $e');
          }

          setState(() {
            _messages.add({
              'role': 'assistant',
              'content': responseText,
              'audio_path': audioPath,
              'time': _currentTime(),
            });
            _loading = false;
          });
        } catch (e) {
          setState(() {
            _messages.add({
              'role': 'assistant',
              'content': 'Hitilafu ya sauti: $e\nVoice error: $e',
              'time': _currentTime(),
            });
            _loading = false;
          });
        }
      } else {
        setState(() { _recording = false; });
      }
    } catch (e) {
      setState(() {
        _recording = false;
        _loading = false;
      });
      debugPrint('Stop recording error: $e');
    }
  }

  // ── PHOTO ─────────────────────────────────────────────────────────────────

  Future<void> _pickAndSendPhoto() async {
    // Use image_picker to take/select photo
    // Then send to agent for mineral identification
    // TODO: Implement photo picker integration
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Picha — Coming soon! (Photo feature)')),
    );
  }

  // ── AUDIO PLAYBACK ────────────────────────────────────────────────────────

  Future<void> _playAudio(String path) async {
    try {
      if (_playingAudio) {
        await _audioPlayer.stop();
        setState(() { _playingAudio = false; });
      } else {
        setState(() { _playingAudio = true; });
        await _audioPlayer.play(DeviceFileSource(path));
        _audioPlayer.onPlayerComplete.listen((_) {
          if (mounted) setState(() { _playingAudio = false; });
        });
      }
    } catch (e) {
      setState(() { _playingAudio = false; });
      debugPrint('Audio playback error: $e');
    }
  }

  // ── VOICE SETTINGS ────────────────────────────────────────────────────────

  void _showVoiceSettings() {
    showModalBottomSheet(
      context: context,
      builder: (context) => Container(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Mipangilio ya Sauti', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const Text('Voice Settings', style: TextStyle(fontSize: 14, color: Colors.grey)),
            const SizedBox(height: 24),
            ListTile(
              leading: const Icon(Icons.cloud),
              title: const Text('NVIDIA NIM Cloud'),
              subtitle: const Text('Use cloud AI for voice (online)'),
              trailing: Switch(value: true, onChanged: (v) {}),
            ),
            ListTile(
              leading: const Icon(Icons.phone_android),
              title: const Text('On-Device Model'),
              subtitle: const Text('Use local model (offline)'),
              trailing: Switch(value: false, onChanged: (v) {}),
            ),
            ListTile(
              leading: const Icon(Icons.language),
              title: const Text('Lugha (Language)'),
              subtitle: const Text('Swahili (Kiswahili)'),
              trailing: const Icon(Icons.arrow_forward_ios),
              onTap: () {},
            ),
          ],
        ),
      ),
    );
  }

  String _currentTime() {
    final now = DateTime.now();
    return '${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}';
  }
}
