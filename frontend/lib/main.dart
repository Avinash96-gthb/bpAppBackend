import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';

const String kDefaultBackendUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'https://bpappbackend.onrender.com',
);

void main() {
  runApp(const BPApp());
}

class BPApp extends StatelessWidget {
  const BPApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'BP Frontend',
      theme: ThemeData(colorSchemeSeed: Colors.blue, useMaterial3: true),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  File? _video;
  String _result = 'No result yet';
  bool _loading = false;
  final ImagePicker _picker = ImagePicker();

  Future<void> _recordVideo() async {
    final XFile? file = await _picker.pickVideo(
      source: ImageSource.camera,
      maxDuration: const Duration(seconds: 30),
    );
    if (file == null) return;
    setState(() {
      _video = File(file.path);
    });
  }

  Future<void> _predict() async {
    if (_video == null) {
      setState(() => _result = 'Please select a video first');
      return;
    }

    setState(() {
      _loading = true;
      _result = 'Sending request...';
    });

    try {
      final baseUrl = kDefaultBackendUrl.trim().replaceAll(RegExp(r'/+$'), '');
      final uri = Uri.parse('$baseUrl/predict');
      final req = http.MultipartRequest('POST', uri)
        ..files.add(await http.MultipartFile.fromPath('video', _video!.path));

      final streamed = await req.send();
      final body = await streamed.stream.bytesToString();

      if (streamed.statusCode >= 200 && streamed.statusCode < 300) {
        final data = jsonDecode(body) as Map<String, dynamic>;
        setState(() {
          _result = 'HR: ${data['heart_rate_bpm']} bpm\n'
              'SYS: ${data['systolic_mmhg']} mmHg\n'
              'DIA: ${data['diastolic_mmhg']} mmHg\n'
              'FPS: ${data['fps']}\n'
              'Frames: ${data['frames']}';
        });
      } else {
        setState(() => _result = 'Error ${streamed.statusCode}: $body');
      }
    } catch (e) {
      setState(() => _result = 'Request failed: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('BP Predictor (Flutter + Python)')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Backend: $kDefaultBackendUrl'),
            const SizedBox(height: 12),
            Row(children: [
              ElevatedButton(onPressed: _recordVideo, child: const Text('Record Video')),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  _video == null ? 'No file selected' : _video!.path.split('/').last,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ]),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _loading ? null : _predict,
              child: Text(_loading ? 'Predicting...' : 'Predict BP'),
            ),
            const SizedBox(height: 16),
            SelectableText(_result),
          ],
        ),
      ),
    );
  }
}
