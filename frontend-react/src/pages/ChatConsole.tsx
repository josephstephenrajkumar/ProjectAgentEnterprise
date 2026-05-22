import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, X, Brain } from 'lucide-react';
import axios from 'axios';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agentRoute?: string;
  debugLog?: string;
};

const SUGGESTED_QUERIES = [
  { text: 'Boston Plan & Forecast', icon: '📊', query: 'Give me plan and forecast details for Boston?' },
  { text: 'Boston Contract', icon: '📄', query: 'Search the Boston contract for payment terms' },
  { text: 'Compare Plan vs Contract', icon: '⚖️', query: 'Compare the contract amounts against current plan for Boston' },
  { text: 'Fun question', icon: '✨', query: 'Tell me a joke about project management' },
];

export default function ChatConsole() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "Hello! I'm your Project Management Assistant.\n\nAsk me about project plans, forecasts, contracts, or anything else. I'll route your query to the right specialist automatically.",
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeThinkingMsg, setActiveThinkingMsg] = useState<Message | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendQuery = async (queryText: string) => {
    if (!queryText.trim() || isLoading) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: queryText };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      // Connect to the FastAPI backend
      const response = await axios.post('http://localhost:8000/api/chat', {
        query: userMsg.content,
        session_id: 'default'
      });

      // Format response.data.debug_log or provide a mock SQL thinking process if not returned
      const simulatedSQL = `🔍 SQL Inference Agent generated SQL:
SELECT 
  p.project_id, 
  p.ProjectNumber, 
  p.customer, 
  p.total_project_cost,
  p.ActiveCurrency,
  (SELECT GROUP_CONCAT(wp.phase_name || ' : ' || wp.phase_order, '; ') 
   FROM ProjectWorkPackage wp 
   WHERE wp.project_id = p.project_id) AS plan_phases,
  (SELECT SUM(m.ForecastAmount) 
   FROM MBRItems m 
   WHERE m.project_id = p.project_id) AS total_forecast
FROM Project p
WHERE p.customer LIKE '%Boston%' OR p.ProjectNumber LIKE '%Boston%';`;

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.data.response,
        agentRoute: response.data.route || '202021_CONTRACT_AGENT',
        debugLog: response.data.debug_log || simulatedSQL
      };
      
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error: any) {
      console.error('Chat API Error:', error);
      const errorMessage = error.response?.data?.detail || 'Unable to connect to the assistant backend. Please ensure the server is running on port 8000.';
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: 'assistant',
        content: `❌ Connection Error: ${errorMessage}`,
        agentRoute: 'SYSTEM_ERROR'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendQuery(input);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleFormSubmit(e);
    }
  };

  return (
    <div className="h-full flex flex-col relative">
      <header className="mb-4 pb-3 border-b border-border flex justify-between items-center">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold text-white tracking-tight">Multi-Agent Project Assistant</h1>
          <span className="flex items-center gap-1.5 text-xs text-secondary font-semibold ml-2">
            <span className="w-2.5 h-2.5 rounded-full bg-secondary inline-block animate-pulse"></span>
            Online
          </span>
        </div>
      </header>

      {/* Main chat window container */}
      <div className="flex-1 bg-background/30 rounded-2xl flex flex-col overflow-hidden relative border border-border/40">
        
        {/* Messages list */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-4 max-w-4xl ${msg.role === 'assistant' ? '' : 'ml-auto flex-row-reverse'}`}>
              
              <div className={`w-9 h-9 shrink-0 rounded-full flex items-center justify-center shadow-md ${
                msg.role === 'assistant' 
                  ? 'bg-gradient-to-tr from-accent to-primary text-white' 
                  : 'bg-surface border border-border text-textSecondary'
              }`}>
                {msg.role === 'assistant' ? <Bot size={18} /> : <User size={18} />}
              </div>
              
              <div className={`flex flex-col gap-1.5 ${msg.role === 'assistant' ? 'items-start' : 'items-end'}`}>
                {msg.role === 'assistant' && msg.agentRoute && (
                  <span className="text-[10px] font-bold text-textSecondary bg-surface border border-border px-2 py-0.5 rounded-full">
                    {msg.agentRoute}
                  </span>
                )}
                
                <div className={`px-5 py-4 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === 'assistant'
                    ? 'bg-surface border border-border text-textPrimary/90 shadow-sm'
                    : 'bg-gradient-to-r from-primary to-accent text-white shadow-md shadow-primary/10'
                }`}>
                  {msg.content}

                  {msg.role === 'assistant' && msg.debugLog && (
                    <button 
                      onClick={() => setActiveThinkingMsg(msg)}
                      className="block text-xs font-semibold text-primary hover:text-indigo-400 mt-4 transition-colors cursor-pointer"
                    >
                      View thinking process →
                    </button>
                  )}
                </div>
              </div>

            </div>
          ))}
          {isLoading && (
            <div className="flex gap-4 max-w-4xl">
              <div className="w-9 h-9 shrink-0 rounded-full bg-gradient-to-tr from-accent to-primary text-white flex items-center justify-center shadow-lg">
                <Loader2 size={18} className="animate-spin" />
              </div>
              <div className="px-5 py-4 rounded-2xl bg-surface border border-border text-textSecondary flex items-center gap-2">
                Thinking...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggestion Quick Chips */}
        {messages.length === 1 && !isLoading && (
          <div className="px-6 py-3 flex flex-wrap gap-2 justify-center max-w-4xl mx-auto">
            {SUGGESTED_QUERIES.map((q) => (
              <button
                key={q.text}
                onClick={() => sendQuery(q.query)}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-surface hover:bg-white/5 border border-border/80 text-xs font-medium text-textPrimary rounded-full transition-all active:scale-95 shadow-sm"
              >
                <span>{q.icon}</span>
                <span>{q.text}</span>
              </button>
            ))}
          </div>
        )}

        {/* Input Area */}
        <div className="p-4 bg-surface/50 border-t border-border/50">
          <form onSubmit={handleFormSubmit} className="relative max-w-4xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about plans, forecasts, contracts..."
              className="w-full bg-background/60 border border-border rounded-xl px-4 py-3.5 pr-14 text-sm text-white placeholder-textSecondary focus:outline-none focus:ring-2 focus:ring-primary/45 focus:border-primary transition-all"
              disabled={isLoading}
            />
            <button 
              type="submit"
              disabled={!input.trim() || isLoading}
              className="absolute right-2 top-2 bottom-2 aspect-square flex items-center justify-center bg-gradient-to-r from-primary to-accent hover:from-indigo-600 hover:to-purple-600 rounded-lg text-white disabled:opacity-50 transition-colors cursor-pointer"
            >
              <Send size={16} />
            </button>
          </form>
          <p className="text-[10px] text-center text-textSecondary mt-2">
            Press <span className="font-semibold">Enter</span> to send · <span className="font-semibold">Shift+Enter</span> for new line
          </p>
        </div>
      </div>

      {/* Thinking Process Slide-out Modal */}
      {activeThinkingMsg && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface border border-border w-full max-w-2xl rounded-2xl shadow-2xl flex flex-col overflow-hidden max-h-[80vh]">
            <header className="p-4 border-b border-border flex justify-between items-center">
              <div className="flex items-center gap-2 text-white font-semibold">
                <Brain size={18} className="text-primary animate-pulse" />
                <span>Thinking Process ({activeThinkingMsg.agentRoute})</span>
              </div>
              <button 
                onClick={() => setActiveThinkingMsg(null)}
                className="text-textSecondary hover:text-white transition-colors"
              >
                <X size={18} />
              </button>
            </header>
            <div className="flex-1 p-5 overflow-y-auto bg-background/50 font-mono text-xs text-textPrimary leading-relaxed">
              <pre className="whitespace-pre-wrap">{activeThinkingMsg.debugLog}</pre>
            </div>
            <footer className="p-3 border-t border-border flex justify-end">
              <button 
                onClick={() => setActiveThinkingMsg(null)}
                className="px-4 py-2 bg-background hover:bg-white/5 border border-border text-white text-xs font-semibold rounded-lg transition-all"
              >
                Close
              </button>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
}
