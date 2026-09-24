import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, LogOut, Plus, Search, FileText, UploadCloud, Trash2, Edit2, Check, X, File as FileIcon } from 'lucide-react';
import { useDocuments, useUploadDocument, useDeleteDocument } from '../hooks/useDocuments';
import { useChats, useCreateChat, useRenameChat, useDeleteChat } from '../hooks/useChats';
import { useLogout } from '../hooks/useAuth';


function FileBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    pdf: 'bg-red-900/40 text-red-400 border-red-800',
    docx: 'bg-blue-900/40 text-blue-400 border-blue-800',
    txt: 'bg-slate-700 text-slate-300 border-slate-600',
  };
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase ${colors[type] ?? colors.txt}`}>
      {type}
    </span>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const logout = useLogout();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState('');

  const { data: documents = [], isLoading: docsLoading } = useDocuments();
  const { data: chats = [], isLoading: chatsLoading } = useChats();
  const uploadMutation = useUploadDocument();
  const deleteMutation = useDeleteDocument();
  const createChatMutation = useCreateChat();
  const renameChatMutation = useRenameChat();
  const deleteChatMutation = useDeleteChat();

  const [editingChatId, setEditingChatId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');


  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError('');
    uploadMutation.mutate(file, {
      onError: (err: any) => {
        const detail = err.response?.data?.detail;
        let message = 'Upload failed';
        if (typeof detail === 'string') {
          message = detail;
        } else if (Array.isArray(detail)) {
          message = detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ');
        }
        setUploadError(message);
      },
    });
    // Reset input so same file can be re-uploaded if deleted
    e.target.value = '';
  };

  const handleNewChat = () => {
    createChatMutation.mutate('New Chat', {
      onSuccess: (chat: any) => navigate(`/chat/${chat.id}`),
    });
  };

  const handleDeleteParams = (id: string, filename: string) => {
    if (window.confirm(`Are you sure you want to delete ${filename}? This will permanently remove its semantic embeddings from the Vector Store.`)) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Navbar */}
      <nav className="border-b border-slate-800 px-6 py-4 flex items-center justify-between bg-slate-900/60 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-sm shadow-inner shadow-blue-500/20">
            <Bot size={18} />
          </div>
          <span className="font-semibold text-lg tracking-tight">DocSearch</span>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors border border-transparent hover:border-slate-800 py-1.5 px-3 rounded-lg"
        >
          <LogOut size={16} /> Sign out
        </button>
      </nav>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar — Chat History */}
        <aside className="w-64 border-r border-slate-800 bg-slate-900/40 flex flex-col">
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
            {chatsLoading ? (
              <p className="text-xs text-slate-500 text-center mt-4">Loading chats…</p>
            ) : chats.length === 0 ? (
              <p className="text-xs text-slate-500 text-center mt-4">No chats yet.</p>
            ) : (
              chats.map((chat: any) => {
                const isEditing = editingChatId === chat.id;

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
                    className="group flex items-center justify-between px-3 py-2.5 rounded-lg transition-colors cursor-pointer text-slate-300 hover:bg-slate-800 hover:text-white"
                    onClick={() => navigate(`/chat/${chat.id}`)}
                  >
                    <div className="flex items-center gap-3 min-w-0 pr-2">
                      <Search size={14} className="text-slate-500 group-hover:text-blue-400 transition-colors flex-shrink-0" />
                      <span className="text-sm truncate font-medium">{chat.title}</span>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingChatId(chat.id);
                          setEditingTitle(chat.title);
                        }}
                        className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-slate-200 transition-all p-1 rounded hover:bg-slate-700/50"
                        title="Rename chat"
                      >
                        <Edit2 size={13} />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm(`Are you sure you want to delete the chat "${chat.title}"?`)) {
                            deleteChatMutation.mutate(chat.id);
                          }
                        }}
                        className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-all p-1 rounded hover:bg-red-400/10"
                        title="Delete chat"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>

        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-4xl mx-auto">
            <h1 className="text-2xl font-bold mb-1">Document Library</h1>
            <p className="text-slate-400 text-sm mb-8">Upload PDF, DOCX, or TXT files to enable AI-powered search and chat.</p>

            {/* Upload Card */}
            <div
              onClick={() => !uploadMutation.isPending && fileRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center transition-all mb-8 ${uploadMutation.isPending ? 'border-blue-500/50 bg-blue-900/10 cursor-wait' : 'border-slate-700 hover:border-blue-500 bg-slate-900/30 hover:bg-slate-900/60 cursor-pointer shadow-sm hover:shadow-md'}`}
            >
              <div className="w-12 h-12 rounded-full bg-blue-600/20 flex items-center justify-center mb-4">
                <UploadCloud size={24} className={uploadMutation.isPending ? 'text-blue-400 animate-bounce' : 'text-blue-400'} />
              </div>
              {uploadMutation.isPending ? (
                <p className="text-sm text-blue-400 font-medium animate-pulse">Extracting and embedding chunks…</p>
              ) : (
                <>
                  <p className="text-sm font-medium text-slate-300">Click to upload a document</p>
                  <p className="text-xs text-slate-500 mt-1">PDF, DOCX, or TXT — max 50 MB</p>
                </>
              )}
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileChange}
                className="hidden"
              />
            </div>

            {uploadError && (
              <div className="bg-red-900/30 border border-red-700 text-red-400 text-sm px-4 py-3 rounded-lg mb-6 flex items-center gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-red-400" /> {uploadError}
              </div>
            )}

            {/* Document List */}
            <h2 className="text-lg font-semibold mb-4">Uploaded Documents</h2>
            {docsLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 bg-slate-800/50 rounded-xl animate-pulse" />
                ))}
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-16 text-slate-500 flex flex-col items-center">
                <FileIcon size={48} className="text-slate-800 mb-4" />
                <p className="text-sm font-medium text-slate-400">No documents uploaded yet</p>
                <p className="text-xs mt-1">Upload your first document above to get started.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {documents.map((doc: any) => (
                  <div
                    key={doc.id}
                    className="group flex items-center justify-between bg-slate-900 border border-slate-800 rounded-xl px-5 py-4 hover:border-slate-700 transition-colors shadow-sm"
                  >
                    <div className="flex items-center gap-4 min-w-0">
                      <FileText size={18} className="text-slate-500 flex-shrink-0" />
                      <span className="text-sm font-medium text-slate-200 truncate pr-2">{doc.filename}</span>
                      <FileBadge type={doc.file_type} />
                    </div>
                    <div className="flex items-center gap-6 ml-4 flex-shrink-0">
                      <span className="text-xs text-slate-500 font-medium">
                        {new Date(doc.uploaded_at).toLocaleDateString()}
                      </span>
                      <button
                        onClick={() => handleDeleteParams(doc.id, doc.filename)}
                        disabled={deleteMutation.isPending && deleteMutation.variables === doc.id}
                        className="text-slate-500 hover:text-red-400 transition-colors p-1.5 rounded hover:bg-red-400/10"
                        title="Delete document"
                      >
                        <Trash2 size={16} className={deleteMutation.isPending && deleteMutation.variables === doc.id ? 'animate-pulse opacity-50' : ''} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
