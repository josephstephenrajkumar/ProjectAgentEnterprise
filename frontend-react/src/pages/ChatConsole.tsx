import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import axios from 'axios';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agentRoute?: string;
  debugLog?: string;
};

export default function ChatConsole() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I am your Project Intelligence Agent. I can help you analyze financial forecasts, search contracts, check RAID logs, or calculate metrics. How can I assist you today?',
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      // Connect to the FastAPI backend
      const response = await axios.post('http://localhost:8000/api/chat', {
        query: userMsg.content,
        session_id: 'default'
      });

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.data.response,
        agentRoute: response.data.route,
        debugLog: response.data.debug_log
      };
      
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      console.error('Chat API Error:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '⚠️ Failed to connect to the agent backend. Ensure FastAPI is running on port 8000.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      <header className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Agent Console</h1>
          <p className="text-textSecondary mt-2">Chat with the LangGraph specialist mesh.</p>
        </div>
      </header>

      <div className="flex-1 glass-panel rounded-2xl flex flex-col overflow-hidden shadow-2xl shadow-black/50">
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-4 max-w-4xl ${msg.role === 'assistant' ? '' : 'ml-auto flex-row-reverse'}`}>
              
              <div className={`w-10 h-10 shrink-0 rounded-full flex items-center justify-center shadow-lg ${
                msg.role === 'assistant' 
                  ? 'bg-gradient-to-tr from-accent to-primary text-white' 
                  : 'bg-surface border border-border text-textSecondary'
              }`}>
                {msg.role === 'assistant' ? <Bot size={20} /> : <User size={20} />}
              </div>
              
              <div className={`flex flex-col gap-1 ${msg.role === 'assistant' ? '' : 'items-end'}`}>
                {msg.role === 'assistant' && msg.agentRoute && (
                  <span className="text-xs font-mono text-primary/80 bg-primary/10 px-2 py-0.5 rounded border border-primary/20 inline-block w-fit">
                    [{msg.agentRoute}]
                  </span>
                )}
                
                <div className={`px-5 py-4 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === 'assistant'
                    ? 'bg-surface/80 border border-white/5 text-textPrimary shadow-sm'
                    : 'bg-primary text-white shadow-md shadow-primary/20'
                }`}>
                  {msg.content}
                </div>
              </div>

            </div>
          ))}
          {isLoading && (
            <div className="flex gap-4 max-w-4xl">
              <div className="w-10 h-10 shrink-0 rounded-full bg-gradient-to-tr from-accent to-primary text-white flex items-center justify-center shadow-lg">
                <Loader2 size={20} className="animate-spin" />
              </div>
              <div className="px-5 py-4 rounded-2xl bg-surface/80 border border-white/5 text-textSecondary flex items-center gap-2">
                Thinking...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 bg-surface/50 border-t border-border/50">
          <form onSubmit={handleSend} className="relative max-w-4xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about your projects..."
              className="w-full bg-background/50 border border-border rounded-xl px-4 py-4 pr-14 text-white placeholder-textSecondary focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
              disabled={isLoading}
            />
            <button 
              type="submit"
              disabled={!input.trim() || isLoading}
              className="absolute right-2 top-2 bottom-2 aspect-square flex items-center justify-center bg-primary rounded-lg text-white hover:bg-blue-600 disabled:opacity-50 disabled:hover:bg-primary transition-colors"
            >
              <Send size={18} className="ml-1" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
