import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';
import '../../../core/theme/app_theme.dart';
import '../providers/research_review_provider.dart';

class _ChatMessage {
  final String role; // 'ai' | 'user'
  final String text;
  final DateTime timestamp;
  final bool isError;

  const _ChatMessage({
    required this.role,
    required this.text,
    required this.timestamp,
    this.isError = false,
  });
}

class ContextualChatScreen extends ConsumerStatefulWidget {
  final String signalId;

  const ContextualChatScreen({super.key, required this.signalId});

  @override
  ConsumerState<ContextualChatScreen> createState() => _ContextualChatScreenState();
}

class _ContextualChatScreenState extends ConsumerState<ContextualChatScreen> {
  final List<_ChatMessage> _messages = [];
  bool _isLoading = false;
  String? _retryText;
  final _textController = TextEditingController();
  final _scrollController = ScrollController();

  static const _fastapiUrl = String.fromEnvironment(
    'FASTAPI_URL',
    defaultValue: 'http://localhost:8000',
  );

  @override
  void initState() {
    super.initState();
    _messages.add(_ChatMessage(
      role: 'ai',
      text: '이 리뷰에 대해 궁금한 점을 물어보세요.',
      timestamp: DateTime.now(),
    ));
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _handleSend({String? overrideText}) async {
    final text = (overrideText ?? _textController.text).trim();
    if (text.isEmpty || _isLoading) return;

    _textController.clear();
    setState(() {
      _retryText = null;
      _messages.add(_ChatMessage(role: 'user', text: text, timestamp: DateTime.now()));
      _isLoading = true;
    });
    _scrollToBottom();

    final reply = await _postChatMessage(text);

    if (!mounted) return;
    setState(() {
      _isLoading = false;
      if (reply != null) {
        _messages.add(_ChatMessage(role: 'ai', text: reply, timestamp: DateTime.now()));
      } else {
        _messages.add(_ChatMessage(
          role: 'ai',
          text: '응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요.',
          timestamp: DateTime.now(),
          isError: true,
        ));
        _retryText = text;
      }
    });
    _scrollToBottom();
  }

  Future<String?> _postChatMessage(String userMessage) async {
    try {
      final session = Supabase.instance.client.auth.currentSession;
      final token = session?.accessToken ?? '';
      final response = await http.post(
        Uri.parse('$_fastapiUrl/api/v1/chat/messages'),
        headers: {
          'Content-Type': 'application/json',
          if (token.isNotEmpty) 'Authorization': 'Bearer $token',
        },
        body: jsonEncode({'signal_id': widget.signalId, 'message': userMessage}),
      );
      if (response.statusCode == 200) {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        return body['data']?['reply'] as String?;
      }
      return null;
    } catch (_) {
      return null;
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final reviewAsync = ref.watch(reviewStateProvider(widget.signalId));
    final signalTitle = reviewAsync.when(
      data: (state) => state is ReviewCompleted ? state.review.signalTitle : null,
      loading: () => null,
      error: (_, __) => null,
    );

    final appBarTitle = signalTitle != null
        ? '리서치 리뷰 — $signalTitle'
        : '리서치 리뷰';

    return Scaffold(
      backgroundColor: AppColors.surfaceBase,
      appBar: AppBar(
        backgroundColor: AppColors.surfaceBase,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          color: AppColors.textPrimary,
          onPressed: () => context.pop(),
        ),
        title: Text(
          appBarTitle,
          style: const TextStyle(
            fontSize: 13,
            color: AppColors.textSecondary,
            fontWeight: FontWeight.w500,
          ),
        ),
        titleSpacing: 0,
      ),
      body: Column(
        children: [
          const Divider(height: 1, color: AppColors.borderSubtle),
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              itemCount: _messages.length + (_isLoading ? 1 : 0),
              itemBuilder: (context, i) {
                if (_isLoading && i == _messages.length) {
                  return _buildLoadingBubble();
                }
                final msg = _messages[i];
                return _buildMessageItem(msg);
              },
            ),
          ),
          _buildInputBar(),
        ],
      ),
    );
  }

  Widget _buildMessageItem(_ChatMessage msg) {
    final isUser = msg.role == 'user';
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          Container(
            constraints: BoxConstraints(
              maxWidth: MediaQuery.of(context).size.width * 0.8,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: isUser ? AppColors.accentPrimary : AppColors.surfaceCard,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              msg.text,
              style: TextStyle(
                fontSize: 15,
                color: isUser ? AppColors.accentForeground : AppColors.textPrimary,
                height: 1.5,
              ),
            ),
          ),
          if (!isUser) ...[
            const SizedBox(height: 4),
            Text(
              '${msg.timestamp.hour.toString().padLeft(2, '0')}:${msg.timestamp.minute.toString().padLeft(2, '0')}',
              style: const TextStyle(
                fontSize: 11,
                color: AppColors.textTertiary,
              ),
            ),
          ],
          if (msg.isError && _retryText != null) ...[
            const SizedBox(height: 6),
            TextButton(
              onPressed: () => _handleSend(overrideText: _retryText),
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                side: const BorderSide(color: AppColors.borderSubtle),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
              ),
              child: const Text(
                '재시도',
                style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildLoadingBubble() {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: AppColors.surfaceCard,
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Text(
          '···',
          style: TextStyle(fontSize: 15, color: AppColors.textTertiary),
        ),
      ),
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
      decoration: const BoxDecoration(
        color: AppColors.surfaceBase,
        border: Border(top: BorderSide(color: AppColors.borderSubtle)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _textController,
              enabled: !_isLoading,
              maxLines: null,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => _handleSend(),
              decoration: InputDecoration(
                hintText: '이 리뷰에 대해 궁금한 점을 물어보세요.',
                hintStyle: const TextStyle(
                  fontSize: 15,
                  color: AppColors.textTertiary,
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
                filled: true,
                fillColor: _isLoading ? AppColors.surfaceRaised : AppColors.surfaceBase,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppColors.borderCard),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppColors.borderCard),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppColors.accentPrimary),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: _isLoading ? null : _handleSend,
            icon: const Icon(Icons.send),
            color: AppColors.accentPrimary,
            disabledColor: AppColors.textDisabled,
            tooltip: '전송',
          ),
        ],
      ),
    );
  }
}
