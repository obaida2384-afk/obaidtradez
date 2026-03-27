import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Send, 
  Bot, 
  User, 
  Loader2,
  RefreshCw,
  Sparkles,
  TrendingUp,
  AlertTriangle
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { API } from "../App";

const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('alphalens_session') || null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (sessionId) {
      loadChatHistory();
    } else {
      setWelcomeMessage();
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const setWelcomeMessage = () => {
    setMessages([{
      role: "assistant",
      content: `# Welcome to AlphaLens AI

I'm your AI investment research assistant. I provide **ranked stock recommendations** with clear, evidence-based reasoning.

## What I Can Help With:

**📊 Investment Ideas**
- "What are the top 5 value stocks right now?"
- "Which tech stocks have the best growth metrics?"
- "Show me undervalued stocks with strong fundamentals"

**📈 Stock Analysis**
- "Analyze AAPL for me"
- "Compare MSFT vs GOOGL"
- "Is NVDA overvalued?"

**🎯 Strategy Questions**
- "What's a good momentum play this week?"
- "Which stocks fit a GARP strategy?"
- "Find me dividend stocks with growth"

**📚 Financial Education**
- "Explain P/E ratio"
- "What's the difference between ROE and ROIC?"
- "How do I calculate intrinsic value?"

---
*⚠️ This is for research purposes only, not financial advice.*`
    }]);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadChatHistory = async () => {
    if (!sessionId) return;
    try {
      const response = await fetch(`${API}/chat/history/${sessionId}`);
      const data = await response.json();
      if (data.length > 0) {
        setMessages(data);
      } else {
        setWelcomeMessage();
      }
    } catch (error) {
      console.error("Error loading history:", error);
      setWelcomeMessage();
    }
  };

  const sendMessage = async (e) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId
        })
      });

      const data = await response.json();
      
      if (!sessionId) {
        setSessionId(data.session_id);
        localStorage.setItem('alphalens_session', data.session_id);
      }

      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: data.response 
      }]);
    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: "I apologize, but I encountered an error processing your request. Please try again." 
      }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const clearChat = () => {
    setSessionId(null);
    localStorage.removeItem('alphalens_session');
    setWelcomeMessage();
  };

  const quickPrompts = [
    "Top 5 value stocks now",
    "Best momentum plays",
    "Analyze AAPL",
    "Compare MSFT vs GOOGL"
  ];

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col" data-testid="chat-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-md bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h1 className="font-heading font-bold text-white">AlphaLens AI</h1>
            <p className="text-xs text-zinc-500">Investment Research Assistant</p>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={clearChat}
          className="text-zinc-400 hover:text-white"
          data-testid="clear-chat-btn"
        >
          <RefreshCw className="w-4 h-4 mr-1" />
          New Chat
        </Button>
      </div>

      {/* Messages */}
      <Card className="terminal-card flex-1 flex flex-col overflow-hidden">
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4 max-w-3xl mx-auto">
            {messages.map((message, i) => (
              <div
                key={i}
                className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-md bg-blue-600/20 border border-blue-500/30 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4 text-blue-400" />
                  </div>
                )}
                
                <div className={`max-w-[85%] ${
                  message.role === 'user' 
                    ? 'chat-message-user px-4 py-3' 
                    : 'chat-message-ai px-4 py-3'
                }`}>
                  {message.role === 'assistant' ? (
                    <div className="markdown-content text-sm">
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <p className="text-sm">{message.content}</p>
                  )}
                </div>
                
                {message.role === 'user' && (
                  <div className="w-8 h-8 rounded-md bg-zinc-800 flex items-center justify-center shrink-0">
                    <User className="w-4 h-4 text-zinc-400" />
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-md bg-blue-600/20 border border-blue-500/30 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-blue-400" />
                </div>
                <div className="chat-message-ai px-4 py-3 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                  <span className="text-sm text-zinc-400">Analyzing...</span>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Quick Prompts */}
        {messages.length <= 1 && (
          <div className="px-4 py-3 border-t border-zinc-800">
            <p className="data-label mb-2">Quick Prompts</p>
            <div className="flex flex-wrap gap-2">
              {quickPrompts.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => setInput(prompt)}
                  className="text-xs px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-md transition-colors"
                  data-testid={`quick-prompt-${i}`}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <form onSubmit={sendMessage} className="p-4 border-t border-zinc-800 bg-zinc-900/50">
          <div className="flex gap-3 max-w-3xl mx-auto">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about stocks, strategies, or market analysis..."
              className="flex-1 h-12 bg-zinc-800 border-zinc-700 focus-visible:ring-blue-500 text-white placeholder:text-zinc-500"
              disabled={isLoading}
              data-testid="chat-input"
            />
            <Button 
              type="submit" 
              size="icon" 
              className="h-12 w-12 bg-blue-600 hover:bg-blue-500"
              disabled={isLoading || !input.trim()}
              data-testid="send-message-btn"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          
          <p className="text-[10px] text-zinc-600 text-center mt-2">
            For research purposes only • Not financial advice
          </p>
        </form>
      </Card>
    </div>
  );
};

export default Chat;
