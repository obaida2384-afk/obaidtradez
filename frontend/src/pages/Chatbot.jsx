import { useState, useEffect, useRef } from "react";
import { useAuth, API } from "../App";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Send, 
  Bot, 
  User, 
  Loader2,
  RefreshCw,
  MessageSquare,
  TrendingUp,
  PiggyBank,
  Sparkles
} from "lucide-react";
import ReactMarkdown from "react-markdown";

const Chatbot = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('obaidtradez_chat_session') || null);
  const [mode, setMode] = useState("general");
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const { token } = useAuth();

  useEffect(() => {
    setWelcomeMessage();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const setWelcomeMessage = () => {
    setMessages([{
      role: "assistant",
      content: `# Welcome to ObaidTradez AI

I'm your AI-powered financial assistant. I can help with both **trading** (short-term) and **investing** (long-term) questions.

## Select a Mode:

**📈 Trading Mode**
- Technical analysis and chart patterns
- Entry/exit timing and momentum plays
- Stop-loss and position sizing
- Short-term trade ideas

**💰 Investing Mode**
- Fundamental analysis and valuation
- DCF models and intrinsic value
- Long-term portfolio construction
- Quality and growth metrics

**🤖 General Mode**
- Any financial question
- Market education and concepts
- Compare trading vs investing approaches
- Portfolio and risk management

---

*Choose a mode above or just ask any question. I'll provide specific, actionable insights with reasoning.*`
    }]);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
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
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
          mode: mode
        })
      });

      const data = await response.json();
      
      if (!sessionId) {
        setSessionId(data.session_id);
        localStorage.setItem('obaidtradez_chat_session', data.session_id);
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
    localStorage.removeItem('obaidtradez_chat_session');
    setWelcomeMessage();
  };

  const quickPrompts = {
    trading: [
      "Best momentum plays today",
      "How to set stop-losses",
      "Analyze TSLA for a trade",
      "Volume breakout strategy"
    ],
    investing: [
      "Top value stocks now",
      "How to calculate DCF",
      "Analyze AAPL fundamentals",
      "Best dividend growers"
    ],
    general: [
      "Trading vs investing?",
      "How to manage risk",
      "Build a portfolio",
      "Market outlook"
    ]
  };

  const getModeConfig = () => ({
    trading: { 
      icon: TrendingUp, 
      color: "text-amber-400",
      bgColor: "bg-amber-500/20",
      borderColor: "border-amber-500/30",
      label: "Trading"
    },
    investing: { 
      icon: PiggyBank, 
      color: "text-emerald-400",
      bgColor: "bg-emerald-500/20",
      borderColor: "border-emerald-500/30",
      label: "Investing"
    },
    general: { 
      icon: MessageSquare, 
      color: "text-blue-400",
      bgColor: "bg-blue-500/20",
      borderColor: "border-blue-500/30",
      label: "General"
    }
  }[mode]);

  const modeConfig = getModeConfig();
  const ModeIcon = modeConfig.icon;

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col" data-testid="chatbot-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-md ${modeConfig.bgColor} border ${modeConfig.borderColor} flex items-center justify-center`}>
            <ModeIcon className={`w-5 h-5 ${modeConfig.color}`} />
          </div>
          <div>
            <h1 className="font-display font-bold text-white">ObaidTradez AI</h1>
            <p className="text-xs text-slate-500">{modeConfig.label} Mode</p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Mode Selector */}
          <Tabs value={mode} onValueChange={setMode}>
            <TabsList className="bg-slate-900 border border-slate-800">
              <TabsTrigger 
                value="trading" 
                className="data-[state=active]:bg-amber-500/20 data-[state=active]:text-amber-400"
              >
                <TrendingUp className="w-4 h-4 mr-1" />
                Trading
              </TabsTrigger>
              <TabsTrigger 
                value="investing"
                className="data-[state=active]:bg-emerald-500/20 data-[state=active]:text-emerald-400"
              >
                <PiggyBank className="w-4 h-4 mr-1" />
                Investing
              </TabsTrigger>
              <TabsTrigger 
                value="general"
                className="data-[state=active]:bg-blue-500/20 data-[state=active]:text-blue-400"
              >
                <MessageSquare className="w-4 h-4 mr-1" />
                General
              </TabsTrigger>
            </TabsList>
          </Tabs>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={clearChat}
            className="text-slate-400 hover:text-white"
            data-testid="clear-chat-btn"
          >
            <RefreshCw className="w-4 h-4 mr-1" />
            New
          </Button>
        </div>
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
                  <div className={`w-8 h-8 rounded-md ${modeConfig.bgColor} border ${modeConfig.borderColor} flex items-center justify-center shrink-0`}>
                    <Bot className={`w-4 h-4 ${modeConfig.color}`} />
                  </div>
                )}
                
                <div className={`max-w-[85%] rounded-lg ${
                  message.role === 'user' 
                    ? 'bg-blue-600 text-white px-4 py-3' 
                    : 'bg-slate-800/50 text-slate-200 px-4 py-3 border border-slate-700'
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
                  <div className="w-8 h-8 rounded-md bg-slate-800 flex items-center justify-center shrink-0">
                    <User className="w-4 h-4 text-slate-400" />
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-3">
                <div className={`w-8 h-8 rounded-md ${modeConfig.bgColor} border ${modeConfig.borderColor} flex items-center justify-center`}>
                  <Bot className={`w-4 h-4 ${modeConfig.color}`} />
                </div>
                <div className="bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-3 flex items-center gap-2">
                  <Loader2 className={`w-4 h-4 animate-spin ${modeConfig.color}`} />
                  <span className="text-sm text-slate-400">Analyzing...</span>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Quick Prompts */}
        {messages.length <= 1 && (
          <div className="px-4 py-3 border-t border-slate-800">
            <p className="text-xs text-slate-500 mb-2">Quick prompts for {modeConfig.label} mode</p>
            <div className="flex flex-wrap gap-2">
              {quickPrompts[mode].map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => setInput(prompt)}
                  className={`text-xs px-3 py-1.5 ${modeConfig.bgColor} ${modeConfig.color} rounded-md transition-colors hover:opacity-80`}
                  data-testid={`quick-prompt-${i}`}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <form onSubmit={sendMessage} className="p-4 border-t border-slate-800 bg-slate-900/50">
          <div className="flex gap-3 max-w-3xl mx-auto">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask about ${mode === 'trading' ? 'trading setups, momentum...' : mode === 'investing' ? 'valuations, fundamentals...' : 'any financial topic...'}`}
              className="flex-1 h-12 bg-slate-800 border-slate-700 focus-visible:ring-blue-500 text-white placeholder:text-slate-500"
              disabled={isLoading}
              data-testid="chat-input"
            />
            <Button 
              type="submit" 
              size="icon" 
              className={`h-12 w-12 ${mode === 'trading' ? 'bg-amber-600 hover:bg-amber-500' : mode === 'investing' ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-blue-600 hover:bg-blue-500'}`}
              disabled={isLoading || !input.trim()}
              data-testid="send-message-btn"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          
          <p className="text-[10px] text-slate-600 text-center mt-2">
            AI-powered insights • For educational purposes only
          </p>
        </form>
      </Card>
    </div>
  );
};

export default Chatbot;
