import React, { useState, useRef, useEffect, useCallback } from 'react';
import { MessageSquare, X, Send, Loader2, Sparkles, Wrench } from 'lucide-react';
import { sendChatMessage } from '../api/client';

const WELCOME_MESSAGE = {
  role: 'assistant',
  content:
    "Hi! I'm your FinOps assistant. Ask me about your Azure spend, M365 licenses, or any cost-optimization question — I can pull live data from your subscription when needed.\n\nTry:\n• *What's my top Azure cost service this month?*\n• *How many unused M365 licenses do I have?*\n• *What would I save by right-sizing VMs?*",
};

function formatContent(text) {
  // Lightweight markdown rendering: bold, italic, line breaks, bullets
  if (!text) return null;
  const lines = text.split('\n');
  return lines.map((line, i) => {
    const key = `l-${i}`;
    if (/^\s*[-*•]\s+/.test(line)) {
      const content = line.replace(/^\s*[-*•]\s+/, '');
      return (
        <div key={key} className="flex gap-2 leading-snug">
          <span className="text-gray-500 flex-shrink-0">•</span>
          <span dangerouslySetInnerHTML={{ __html: inlineFormat(content) }} />
        </div>
      );
    }
    if (!line.trim()) return <div key={key} className="h-2" />;
    return (
      <div
        key={key}
        className="leading-snug"
        dangerouslySetInnerHTML={{ __html: inlineFormat(line) }}
      />
    );
  });
}

function inlineFormat(text) {
  // Escape HTML first
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  // Bold **text**
  return escaped
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code class="bg-gray-800 text-blue-300 px-1 rounded text-xs">$1</code>');
}

function Message({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`rounded-2xl px-3.5 py-2 text-sm max-w-[85%] ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-md'
            : 'bg-gray-700 text-gray-100 rounded-bl-md'
        }`}
      >
        <div className="space-y-0.5">{formatContent(msg.content)}</div>
        {msg.tools_used && msg.tools_used.length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-600/50 flex items-center gap-1 text-[10px] text-gray-400">
            <Wrench className="w-3 h-3" />
            <span>Used: {msg.tools_used.join(', ')}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function ChatAgent() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending]);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen]);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || sending) return;

    const userMsg = { role: 'user', content: trimmed };
    // Build history excluding the welcome message (which isn't part of real convo)
    const history = messages
      .filter((m) => m !== WELCOME_MESSAGE)
      .map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setSending(true);
    setError(null);

    try {
      const result = await sendChatMessage(trimmed, history);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: result.reply,
          tools_used: result.tools_used,
        },
      ]);
    } catch (err) {
      setError(err.message);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, I hit an error: ${err.message}`,
        },
      ]);
    } finally {
      setSending(false);
    }
  }, [input, sending, messages]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleReset = () => {
    setMessages([WELCOME_MESSAGE]);
    setError(null);
  };

  return (
    <>
      {/* Floating Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-full shadow-lg shadow-blue-900/40 transition-all hover:scale-105"
        >
          <MessageSquare className="w-5 h-5" />
          <span className="font-medium text-sm pr-1">Chat with Me</span>
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div className="fixed bottom-6 right-6 z-40 w-[380px] max-w-[calc(100vw-3rem)] h-[560px] max-h-[calc(100vh-3rem)] bg-gray-800 border border-gray-700 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gray-800">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div>
                <p className="text-white font-semibold text-sm leading-tight">FinOps Assistant</p>
                <p className="text-blue-400 text-xs">Powered by Claude</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={handleReset}
                className="text-gray-400 hover:text-white text-xs px-2 py-1 rounded hover:bg-gray-700"
                title="Reset conversation"
              >
                Reset
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-gray-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-gray-850 bg-gray-900/50"
          >
            {messages.map((msg, idx) => (
              <Message key={idx} msg={msg} />
            ))}

            {sending && (
              <div className="flex justify-start">
                <div className="bg-gray-700 rounded-2xl rounded-bl-md px-3.5 py-2.5 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
                  <span className="text-gray-300 text-xs">Thinking...</span>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-gray-700 p-3 bg-gray-800">
            <div className="flex items-end gap-2 bg-gray-700 rounded-xl px-3 py-2 border border-gray-600 focus-within:border-blue-500">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your cloud spend..."
                rows={1}
                className="flex-1 bg-transparent text-white text-sm placeholder-gray-500 focus:outline-none resize-none max-h-24"
                disabled={sending}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || sending}
                className="p-1.5 text-blue-400 hover:text-blue-300 disabled:text-gray-600 disabled:cursor-not-allowed rounded-lg"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            <p className="text-gray-600 text-[10px] mt-1.5 text-center">
              Responses may be based on live Azure/M365 data
            </p>
          </div>
        </div>
      )}
    </>
  );
}

export default ChatAgent;