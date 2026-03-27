import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { 
  Send, 
  Bot, 
  User, 
  TrendingUp, 
  TrendingDown,
  RefreshCw,
  Sparkles,
  Search,
  MessageSquare,
  Loader2
} from "lucide-react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ObaidChat = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(() => {
    return localStorage.getItem('obaid_session') || null;
  });
  const [stockSymbol, setStockSymbol] = useState("");
  const [stockData, setStockData] = useState(null);
  const [isLoadingStock, setIsLoadingStock] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (sessionId) {
      loadChatHistory();
    } else {
      // Add welcome message
      setMessages([{
        role: "assistant",
        content: "Hello! I'm **Obaid**, your AI financial assistant. I can help you with:\n\n- **Financial Formulas** (ROI, NPV, IRR, P/E ratio, etc.)\n- **Stock Analysis** (Use the stock lookup on the right)\n- **Revenue Predictions** & Growth Analysis\n- **Financial Education** & Concepts\n\nHow can I assist you today?"
      }]);
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadChatHistory = async () => {
    if (!sessionId) return;
    try {
      const response = await axios.get(`${API}/chat/history/${sessionId}`);
      if (response.data.length > 0) {
        setMessages(response.data);
      } else {
        setMessages([{
          role: "assistant",
          content: "Hello! I'm **Obaid**, your AI financial assistant. I can help you with:\n\n- **Financial Formulas** (ROI, NPV, IRR, P/E ratio, etc.)\n- **Stock Analysis** (Use the stock lookup on the right)\n- **Revenue Predictions** & Growth Analysis\n- **Financial Education** & Concepts\n\nHow can I assist you today?"
        }]);
      }
    } catch (error) {
      console.error("Error loading history:", error);
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
      const response = await axios.post(`${API}/chat`, {
        message: userMessage,
        session_id: sessionId
      });

      const newSessionId = response.data.session_id;
      if (!sessionId) {
        setSessionId(newSessionId);
        localStorage.setItem('obaid_session', newSessionId);
      }

      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: response.data.response 
      }]);
    } catch (error) {
      console.error("Chat error:", error);
      toast.error("Failed to get response. Please try again.");
      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: "I apologize, but I encountered an error. Please try again." 
      }]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const lookupStock = async (e) => {
    e?.preventDefault();
    if (!stockSymbol.trim() || isLoadingStock) return;

    setIsLoadingStock(true);
    setStockData(null);

    try {
      const response = await axios.get(`${API}/stock/${stockSymbol.toUpperCase()}`);
      setStockData(response.data);
      
      if (response.data.error) {
        toast.error(response.data.error);
      }
    } catch (error) {
      console.error("Stock lookup error:", error);
      toast.error("Failed to fetch stock data");
    } finally {
      setIsLoadingStock(false);
    }
  };

  const clearChat = () => {
    setMessages([{
      role: "assistant",
      content: "Hello! I'm **Obaid**, your AI financial assistant. How can I help you today?"
    }]);
    setSessionId(null);
    localStorage.removeItem('obaid_session');
  };

  const suggestedQuestions = [
    "What is the P/E ratio formula?",
    "Explain compound interest",
    "How to calculate ROI?",
    "What is WACC?"
  ];

  return (
    <div className="min-h-screen pt-16" data-testid="obaid-chat-page">
      <div className="h-[calc(100vh-4rem)] grid lg:grid-cols-[1fr_380px]">
        {/* Chat Panel */}
        <div className="flex flex-col h-full border-r border-border">
          {/* Chat Header */}
          <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-background/95 backdrop-blur">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h2 className="font-display font-semibold">Obaid</h2>
                <p className="text-xs text-muted-foreground font-mono">AI Financial Assistant</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearChat}
              className="font-mono text-xs"
              data-testid="clear-chat-btn"
            >
              <RefreshCw className="h-3 w-3 mr-2" />
              New Chat
            </Button>
          </div>

          {/* Messages */}
          <ScrollArea className="flex-1 px-6 py-4">
            <div className="space-y-6 max-w-3xl mx-auto">
              <AnimatePresence>
                {messages.map((message, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    {message.role === 'assistant' && (
                      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                        <Bot className="h-4 w-4 text-primary" />
                      </div>
                    )}
                    <div className={`max-w-[80%] ${
                      message.role === 'user' 
                        ? 'chat-bubble-user px-4 py-3' 
                        : 'chat-bubble-ai px-4 py-3'
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
                      <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center shrink-0">
                        <User className="h-4 w-4" />
                      </div>
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>

              {isLoading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex gap-4"
                >
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <div className="chat-bubble-ai px-4 py-3 flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm text-muted-foreground">Thinking...</span>
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Suggested Questions */}
          {messages.length <= 1 && (
            <div className="px-6 py-3 border-t border-border">
              <p className="text-xs text-muted-foreground mb-2 font-mono uppercase tracking-wider">Suggested Questions</p>
              <div className="flex flex-wrap gap-2">
                {suggestedQuestions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(q)}
                    className="text-xs px-3 py-1.5 border border-border hover:border-primary/50 hover:bg-primary/5 transition-colors"
                    data-testid={`suggested-question-${i}`}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <form onSubmit={sendMessage} className="p-4 border-t border-border bg-background">
            <div className="flex gap-3 max-w-3xl mx-auto">
              <Input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about finance, formulas, stocks..."
                className="flex-1 h-12 border-border focus-visible:ring-primary"
                disabled={isLoading}
                data-testid="chat-input"
              />
              <Button 
                type="submit" 
                size="icon" 
                className="h-12 w-12"
                disabled={isLoading || !input.trim()}
                data-testid="send-message-btn"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </form>
        </div>

        {/* Stock Lookup Panel */}
        <div className="hidden lg:flex flex-col h-full bg-muted/30">
          <div className="px-6 py-4 border-b border-border">
            <h3 className="font-display font-semibold flex items-center gap-2">
              <Search className="h-4 w-4 text-primary" />
              Stock Lookup
            </h3>
            <p className="text-xs text-muted-foreground mt-1">Real-time stock prices</p>
          </div>

          <div className="p-6">
            <form onSubmit={lookupStock} className="flex gap-2 mb-6">
              <Input
                value={stockSymbol}
                onChange={(e) => setStockSymbol(e.target.value.toUpperCase())}
                placeholder="Enter symbol (e.g., AAPL)"
                className="flex-1 h-10 font-mono uppercase"
                data-testid="stock-symbol-input"
              />
              <Button 
                type="submit" 
                size="sm" 
                className="h-10"
                disabled={isLoadingStock}
                data-testid="lookup-stock-btn"
              >
                {isLoadingStock ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              </Button>
            </form>

            {stockData && !stockData.error && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <Card className="p-6 bento-item" data-testid="stock-data-card">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h4 className="font-mono text-lg font-bold">{stockData.symbol}</h4>
                      <p className="text-xs text-muted-foreground">Last updated: {stockData.last_trading_day}</p>
                    </div>
                    {parseFloat(stockData.change) >= 0 ? (
                      <TrendingUp className="h-6 w-6 text-green-500" />
                    ) : (
                      <TrendingDown className="h-6 w-6 text-red-500" />
                    )}
                  </div>

                  <div className="space-y-4">
                    <div>
                      <p className="font-mono text-3xl font-bold">
                        ${parseFloat(stockData.price).toFixed(2)}
                      </p>
                      <div className={`flex items-center gap-2 mt-1 ${
                        parseFloat(stockData.change) >= 0 ? 'text-green-500' : 'text-red-500'
                      }`}>
                        <span className="font-mono text-sm">
                          {parseFloat(stockData.change) >= 0 ? '+' : ''}{parseFloat(stockData.change).toFixed(2)}
                        </span>
                        <span className="font-mono text-sm">
                          ({stockData.change_percent})
                        </span>
                      </div>
                    </div>

                    <div className="pt-4 border-t border-border">
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-muted-foreground font-mono uppercase tracking-wider">Volume</span>
                        <span className="font-mono text-sm">{parseInt(stockData.volume).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>
            )}

            {stockData?.error && (
              <Card className="p-4 border-destructive/50 bg-destructive/5">
                <p className="text-sm text-destructive">{stockData.error}</p>
              </Card>
            )}

            {/* Quick Symbols */}
            <div className="mt-6">
              <p className="text-xs text-muted-foreground font-mono uppercase tracking-wider mb-3">Popular Stocks</p>
              <div className="flex flex-wrap gap-2">
                {['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META'].map(symbol => (
                  <button
                    key={symbol}
                    onClick={() => {
                      setStockSymbol(symbol);
                      lookupStock({ preventDefault: () => {} });
                    }}
                    className="text-xs font-mono px-3 py-1.5 border border-border hover:border-primary/50 hover:bg-primary/5 transition-colors"
                    data-testid={`quick-stock-${symbol}`}
                  >
                    {symbol}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* AI Tips */}
          <div className="mt-auto p-6 border-t border-border">
            <div className="flex items-start gap-3">
              <Sparkles className="h-4 w-4 text-secondary mt-0.5" />
              <div>
                <p className="text-xs font-semibold mb-1">Ask Obaid</p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Try asking about financial ratios, investment strategies, or how to analyze company fundamentals.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ObaidChat;
