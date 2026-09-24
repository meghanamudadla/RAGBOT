import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Send, ArrowLeft, Bot, LogOut, Search, Trash2, Plus, FileQuestion, FileText, Edit2, Check, X, AlertTriangle, ShieldCheck, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { useChatMessages, useDeleteChat, useChats, useCreateChat, useRenameChat } from '../hooks/useChats';
import { useLogout } from '../hooks/useAuth';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';


// ─── Sub-components ────────────────────────────────────────────────

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const configs = {
    high: { label: 'High confidence', icon: ShieldCheck, bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
    medium: { label: 'Review recommended', icon: AlertTriangle, bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30' },
    low: { label: 'Low confidence', icon: AlertCircle, bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' },
  };
  const cfg = configs[confidence as keyof typeof configs] || configs.low;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
      <Icon size={10} />
      {cfg.label}
    </span>
  );
}

function FlaggedClaimsPanel({ sentences }: { sentences: any[] }) {
  const [expanded, setExpanded] = useState(false);
  
  const unsupported = sentences.filter(s => s.status === 'unsupported' && s.citation_ids?.length > 0);
  const noCitation = sentences.filter(s => s.status === 'unsupported' && (!s.citation_ids || s.citation_ids.length === 0));
  
  if (!unsupported.length && !noCitation.length) return null;

  return (
    <div className="mt-4 border-t border-slate-700/60 pt-4 flex flex-col items-start w-full break-words">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-[11px] font-bold text-slate-500 uppercase tracking-widest hover:text-slate-300 transition-colors"
      >
        <AlertTriangle size={12} />
        Claims not directly supported by your documents
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {expanded && (
        <div className="mt-2 space-y-2 w-full">
          {unsupported.map((s: any, i: number) => (
            <div key={`unsup-${i}`} className="flex items-start gap-2.5 text-xs text-slate-400 group">
              <span className="mt-0.5 w-5 h-5 rounded bg-red-500/20 flex items-center justify-center flex-shrink-0 font-bold text-red-400">
                {s.citation_ids?.join(',') || '?'}
              </span>
              <span className="flex-1 overflow-hidden text-slate-300">{s.text}</span>
            </div>
          ))}
          {noCitation.map((s: any, i: number) => (
            <div key={`nocite-${i}`} className="flex items-start gap-2.5 text-xs text-slate-400 group">
              <span className="mt-0.5 w-5 h-5 rounded bg-slate-600/50 flex items-center justify-center flex-shrink-0 font-bold text-slate-400">
                —
              </span>
              <span className="flex-1 overflow-hidden text-slate-300">{s.text} <span className="text-slate-500 italic">(no citation)</span></span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CitationsPanel({ citations }: { citations: any[] }) {
  if (!citations?.length) return null;
  return (
    <div className="mt-4 border-t border-slate-700/60 pt-4 space-y-2 flex flex-col items-start w-full break-words">
      <p className="text-[11px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
        <FileText size={12} /> Sources Found
      </p>
      {citations.map((c: any, i: number) => (
        <div key={i} className="flex items-start gap-2.5 text-xs text-slate-400 w-full group">
          <span className="mt-0.5 w-5 h-5 rounded bg-slate-700/50 flex items-center justify-center flex-shrink-0 font-bold group-hover:bg-blue-600/20 group-hover:text-blue-400 transition-colors">
            {i + 1}
          </span>
          <span className="flex-1 overflow-hidden">
            <span className="text-slate-300 font-medium break-words block">{c.filename ?? 'Document'}</span>
            {c.chunk_index !== undefined && (
              <span className="text-slate-500 text-[11px]">Chunk {c.chunk_index}</span>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}

function MessageBubble({ msg }: { msg: any }) {
  const isUser = msg.role === 'user';
  const groundedness = msg.groundedness;
  const confidence = groundedness?.overall_confidence || 'low';
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-blue-600/20 text-blue-400 border border-blue-600/30 flex items-center justify-center mr-3 flex-shrink-0 mt-1 shadow-sm">
          <Bot size={16} />
        </div>
      )}
      <div
        className={`max-w-3xl rounded-2xl px-5 py-4 text-sm leading-relaxed overflow-x-auto shadow-sm ${
          isUser
            ? 'bg-blue-600 text-white rounded-tr-sm whitespace-pre-wrap'
            : 'bg-slate-800/80 text-slate-100 rounded-tl-sm border border-slate-700/50 prose prose-invert prose-sm prose-p:leading-relaxed prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-700 max-w-none'
        }`}
      >
        {isUser ? (
          msg.content
        ) : (
          <>
            {!isUser && groundedness && (
              <div className="mb-3 flex items-center justify-between">
                <ConfidenceBadge confidence={confidence} />
              </div>
            )}
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {msg.content}
            </ReactMarkdown>
            {!isUser && <CitationsPanel citations={msg.citations} />}
            {!isUser && groundedness && <FlaggedClaimsPanel sentences={groundedness.sentences} />}
          </>
        )}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start mb-6">
      <div className="w-8 h-8 rounded-full bg-blue-600/20 text-blue-400 border border-blue-600/30 flex items-center justify-center mr-3 flex-shrink-0 mt-1 shadow-sm">
        <Bot size={16} />
      </div>
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm">
        <div className="flex gap-1.5 items-center mt-1">
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-bounce [animation-delay:0ms]" />
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-bounce [animation-delay:150ms]" />
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}

// ─── Main Chat Page ─────────────────────────────────────────────────

export default function ChatPage() {
  const { chatId } = useParams<{ chatId: string }>();
  const navigate = useNavigate();
  const logout = useLogout();
  const queryClient = useQueryClient();
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingError, setStreamingError] = useState('');
  const [streamingMessage, setStreamingMessage] = useState<any>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isStreamingRef = useRef(false);

  const { data: chats = [] } = useChats();
  const createChatMutation = useCreateChat();
  const deleteChatMutation = useDeleteChat();
  const renameChatMutation = useRenameChat();
  const { data: chatDetail, isLoading } = useChatMessages(chatId!);

  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

  const messages = useMemo(
    () => (streamingMessage ? [...(chatDetail?.messages ?? []), streamingMessage] : (chatDetail?.messages ?? [])),
    [chatDetail, streamingMessage]
  );


  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreamingRef.current) return;
    
    isStreamingRef.current = true;
    const userMessage = input.trim();
    setInput('');
    setStreamingError('');
    setIsStreaming(true);

    const tempUserMsgId = crypto.randomUUID();
    queryClient.setQueryData(['chat', chatId], (old: any) => {
      if (!old) return old;
      return {
        ...old,
        messages: [
          ...(old.messages || []),
          { id: tempUserMsgId, role: 'user', content: userMessage, created_at: new Date().toISOString() }
        ]
      };
    });

    const tempAiMsgId = crypto.randomUUID();
    setStreamingMessage({ id: tempAiMsgId, role: 'assistant', content: '', citations: [], groundedness: null });

    let streamFailed = false;
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/chat/${chatId}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ content: userMessage })
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let aiContent = '';
      let citations: any[] = [];
      let groundedness: any = null;
      let finalMessageId = tempAiMsgId;

      if (reader) {
        // Buffer partial lines: a stream chunk may split a `data: ...` line
        // mid-JSON, so we must carry the incomplete line over to the next chunk.
        let buffer = '';
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const dataStr = line.replace('data: ', '').trim();
            if (!dataStr) continue;

            let data;
            try {
              data = JSON.parse(dataStr);
            } catch {
              continue; // malformed/partial event — skip rather than kill the stream
            }

            if (data.token) {
              aiContent += data.token;
              setStreamingMessage((prev: any) => prev ? { ...prev, content: aiContent } : null);
            }
            if (data.done) {
              citations = data.citations || [];
              groundedness = data.groundedness || null;
              finalMessageId = data.message_id || tempAiMsgId;
              setStreamingMessage((prev: any) => prev ? { ...prev, citations, groundedness, id: finalMessageId } : null);
            }
            if (data.error) {
              streamFailed = true;
              setStreamingError(data.error);
            }
          }
        }
      }

      setStreamingMessage(null);
      if (!streamFailed) {
        queryClient.setQueryData(['chat', chatId], (old: any) => {
          if (!old) return old;
          return {
            ...old,
            messages: [
              ...(old.messages || []),
              { id: finalMessageId, role: 'assistant', content: aiContent, citations, groundedness: groundedness, created_at: new Date().toISOString() }
            ]
          };
        });
        // Re-sync with the server (replaces the optimistic temp message ids
        // with the persisted ones).
        queryClient.invalidateQueries({ queryKey: ['chat', chatId] });
      }

    } catch (err: any) {
      console.error(err);
      setStreamingMessage(null);
      setStreamingError(err.message || 'Stream connection failed');
    } finally {
      isStreamingRef.current = false;
      setIsStreaming(false);
    }
  };

  const handleNewChat = () => {
    createChatMutation.mutate('New Chat', {
      onSuccess: (chat: any) => navigate(`/chat/${chat.id}`),
    });
  };

  const handleDeleteParams = (id: string, title: string) => {
    if (window.confirm(`Are you sure you want to delete the chat "${title}"?`)) {
      deleteChatMutation.mutate(id, {
        onSuccess: () => {
          if (id === chatId) navigate('/');
        },
      });
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Navbar */}
      <nav className="border-b border-slate-800 px-6 py-4 flex items-center justify-between bg-slate-900/60 backdrop-blur flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/')} className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-sm shadow-inner shadow-blue-500/20">
              <Bot size={18} />
            </div>
            <span className="font-semibold text-lg tracking-tight">DocSearch</span>
          </button>
        </div>
        <button onClick={logout} className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors border border-transparent hover:border-slate-800 py-1.5 px-3 rounded-lg">
          <LogOut size={16} /> Sign out
        </button>
      </nav>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 border-r border-slate-800 bg-slate-900/40 flex flex-col flex-shrink-0">
          <div className="p-4 border-b border-slate-800">
            <button
              onClick={handleNewChat}
              disabled={createChatMutation.isPending}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold py-2.5 px-4 rounded-lg transition-colors disabled:opacity-50"
            >
              <Plus size={16} /> {createChatMutation.isPending ? 'Creating...' : 'New Chat'}
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-1">
            {chats.map((chat: any) => {
              const isEditing = editingChatId === chat.id;
              const isCurrent = chat.id === chatId;

              if (isEditing) {
                return (
                  <form
                    key={chat.id}
                    onSubmit={(e) => {
                      e.preventDefault();
                      if (editingTitle.trim()) {
                        renameChatMutation.mutate({ id: chat.id, title: editingTitle.trim() }, {
                          onSettled: () => setEditingChatId(null),
                        });
                      } else {
                        setEditingChatId(null);
                      }
                    }}
                    className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg bg-slate-800 border border-blue-500"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="text"
                      value={editingTitle}
                      onChange={(e) => setEditingTitle(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Escape') setEditingChatId(null);
                      }}
                      autoFocus
                      className="w-full bg-slate-950 px-2 py-1 text-xs text-white rounded border border-slate-700 outline-none focus:border-blue-400"
                    />
                    <button
                      type="submit"
                      className="text-blue-400 hover:text-blue-300 p-1"
                      title="Save"
                    >
                      <Check size={14} />
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingChatId(null)}
                      className="text-slate-400 hover:text-slate-300 p-1"
                      title="Cancel"
                    >
                      <X size={14} />
                    </button>
                  </form>
                );
              }

              return (
                <div
                  key={chat.id}
                  className={`group flex items-center justify-between px-3 py-2.5 rounded-lg transition-colors cursor-pointer ${
                    isCurrent
                      ? 'bg-blue-600/20 text-white border border-blue-700/50'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                  onClick={() => navigate(`/chat/${chat.id}`)}
                >
                  <div className="flex items-center gap-3 min-w-0 pr-2">
                    <Search size={14} className={isCurrent ? 'text-blue-400' : 'text-slate-500'} flex-shrink-0 />
                    <span className="text-sm truncate font-medium">{chat.title}</span>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingChatId(chat.id);
                        setEditingTitle(chat.title);
                      }}
                      className={`${isCurrent ? 'opacity-100 text-blue-400 hover:text-white' : 'opacity-0 group-hover:opacity-100 text-slate-500 hover:text-slate-200'} transition-all p-1 rounded hover:bg-slate-700/50`}
                      title="Rename chat"
                    >
                      <Edit2 size={13} />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteParams(chat.id, chat.title); }}
                      className={`${isCurrent ? 'opacity-100 text-blue-400 hover:text-red-400' : 'opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400'} transition-all p-1 rounded hover:bg-red-400/10`}
                      title="Delete chat"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="p-4 border-t border-slate-800">
            <button
              onClick={() => navigate('/')}
              className="w-full flex items-center gap-3 text-sm text-slate-400 hover:text-white py-2 px-3 rounded-lg hover:bg-slate-800 transition-colors font-medium border border-transparent hover:border-slate-700"
            >
              <ArrowLeft size={16} /> Back to Documents
            </button>
          </div>
        </aside>

        {/* Chat Area */}
        <main className="flex-1 flex flex-col overflow-hidden relative">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-8">
            <div className="max-w-4xl mx-auto">
              {isLoading ? (
                <div className="flex items-center justify-center h-full text-slate-500 text-sm mt-32">
                  <div className="w-6 h-6 border-2 border-slate-600 border-t-blue-500 rounded-full animate-spin"></div>
                </div>
              ) : messages.length === 0 && !isStreaming ? (
                <div className="flex flex-col items-center justify-center h-[60vh] text-center">
                  <div className="w-16 h-16 rounded-2xl bg-blue-600/10 border border-blue-600/20 flex items-center justify-center mb-5 shadow-inner">
                    <FileQuestion size={32} className="text-blue-500" />
                  </div>
                  <h3 className="text-xl font-bold text-slate-200 mb-2">Ask questions about your data</h3>
                  <p className="text-sm text-slate-400 max-w-sm leading-relaxed">
                    Messages are sent to the AI natively. The system will retrieve relevant context chunks from your synced documents to answer.
                  </p>
                </div>
              ) : (
                <>
                  {messages.map((msg: any) => (
                    <MessageBubble key={msg.id} msg={msg} />
                  ))}
                  {isStreaming && !streamingMessage && <TypingIndicator />}
                  <div ref={bottomRef} className="h-4" />
                </>
              )}
            </div>
          </div>

          {/* Input Bar */}
          <div className="border-t border-slate-800/80 bg-slate-900/80 backdrop-blur-md px-6 py-5 flex-shrink-0 z-10 w-full relative">
            <div className="max-w-4xl mx-auto relative">
              {streamingError && (
                <p className="absolute -top-10 left-0 bg-red-900/60 border border-red-800 text-red-300 text-xs px-3 py-1.5 rounded shadow-lg backdrop-blur flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse"></span> {streamingError}
                </p>
              )}
              <form onSubmit={handleSend} className="relative flex items-end">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(e as any); }
                  }}
                  placeholder="Message DocSearch AI... (Enter to send)"
                  rows={1}
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-2xl pl-5 pr-14 py-3.5 text-[15px] text-slate-100 resize-none outline-none focus:border-blue-500/80 focus:bg-slate-800 transition-all placeholder:text-slate-500 max-h-40 overflow-y-auto shadow-sm"
                  style={{ minHeight: '52px' }}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isStreaming}
                  className="absolute right-2 bottom-2 w-9 h-9 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed text-white rounded-xl flex items-center justify-center transition-all"
                >
                  <Send size={16} className={isStreaming ? 'opacity-0' : 'ml-0.5'} />
                  {isStreaming && <div className="absolute w-4 h-4 border-2 border-slate-400 border-t-white rounded-full animate-spin"></div>}
                </button>
              </form>
              <div className="text-center mt-2">
                 <p className="text-[10px] text-slate-500 flex items-center justify-center gap-1.5"><Bot size={10}/> AI generated content may be inaccurate or hallucinated. Verify facts using citations.</p>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
