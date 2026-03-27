import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { ArrowRight, BarChart3, Bot, FileText, TrendingUp, Shield, Zap } from "lucide-react";

const LandingPage = () => {
  const navigate = useNavigate();

  const features = [
    {
      icon: FileText,
      title: "AI in Finance Report",
      description: "Comprehensive 3-page infographic on how firms use AI agents",
      action: () => navigate('/report'),
      cta: "View Report"
    },
    {
      icon: Bot,
      title: "Meet Obaid",
      description: "Your AI financial assistant for formulas, stocks & predictions",
      action: () => navigate('/chat'),
      cta: "Start Chat"
    },
    {
      icon: TrendingUp,
      title: "Real-time Stocks",
      description: "Get live stock prices from major exchanges worldwide",
      action: () => navigate('/chat'),
      cta: "Check Prices"
    }
  ];

  const stats = [
    { value: "73%", label: "Firms Using AI" },
    { value: "$35B", label: "Annual Investment" },
    { value: "25%", label: "Cost Savings" },
    { value: "24/7", label: "AI Availability" }
  ];

  return (
    <div className="min-h-screen" data-testid="landing-page">
      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center justify-center overflow-hidden hero-gradient">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute inset-0" style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }} />
        </div>

        <div className="container mx-auto px-6 md:px-12 lg:px-24 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center max-w-4xl mx-auto"
          >
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground mb-6"
            >
              AI-Powered Financial Intelligence
            </motion.p>
            
            <h1 className="font-display text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight mb-8 leading-[0.9]">
              The Future of
              <span className="block text-primary">Finance is Here</span>
            </h1>
            
            <p className="font-body text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-12 leading-relaxed">
              Explore how AI agents are transforming financial services. Get real-time insights, 
              stock analysis, and expert financial guidance from Obaid, your AI assistant.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button
                size="lg"
                onClick={() => navigate('/report')}
                className="font-mono uppercase tracking-wider text-sm h-14 px-8 group"
                data-testid="hero-view-report-btn"
              >
                View Infographic Report
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={() => navigate('/chat')}
                className="font-mono uppercase tracking-wider text-sm h-14 px-8"
                data-testid="hero-meet-obaid-btn"
              >
                Meet Obaid AI
              </Button>
            </div>
          </motion.div>

          {/* Stats Row */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.8 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-8 mt-24 max-w-4xl mx-auto"
          >
            {stats.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 + i * 0.1 }}
                className="text-center"
              >
                <p className="font-mono text-4xl md:text-5xl font-bold text-primary mb-2">
                  {stat.value}
                </p>
                <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  {stat.label}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <div className="w-6 h-10 border-2 border-muted-foreground/30 rounded-full flex justify-center">
            <motion.div
              animate={{ y: [0, 12, 0] }}
              transition={{ repeat: Infinity, duration: 1.5 }}
              className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full mt-2"
            />
          </div>
        </motion.div>
      </section>

      {/* Features Section */}
      <section className="py-24 md:py-32 px-6 md:px-12 lg:px-24">
        <div className="container mx-auto max-w-6xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground mb-4">
              What We Offer
            </p>
            <h2 className="font-display text-3xl md:text-5xl font-semibold tracking-tight">
              Financial Intelligence Suite
            </h2>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15 }}
                className="bento-item group cursor-pointer"
                onClick={feature.action}
                data-testid={`feature-card-${i}`}
              >
                <div className="h-12 w-12 rounded-none border border-border flex items-center justify-center mb-6 group-hover:border-primary/50 group-hover:bg-primary/5 transition-all">
                  <feature.icon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="font-display text-xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-muted-foreground mb-6 leading-relaxed">{feature.description}</p>
                <Button
                  variant="ghost"
                  className="font-mono text-xs uppercase tracking-wider p-0 h-auto hover:bg-transparent hover:text-primary group/btn"
                >
                  {feature.cta}
                  <ArrowRight className="ml-2 h-3 w-3 group-hover/btn:translate-x-1 transition-transform" />
                </Button>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Why AI Section */}
      <section className="py-24 md:py-32 px-6 md:px-12 lg:px-24 bg-muted/30">
        <div className="container mx-auto max-w-6xl">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <motion.div
              initial={{ opacity: 0, x: -30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
            >
              <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground mb-4">
                Why AI in Finance?
              </p>
              <h2 className="font-display text-3xl md:text-4xl font-semibold tracking-tight mb-6">
                Transforming Financial Services Through Intelligence
              </h2>
              <p className="text-muted-foreground leading-relaxed mb-8">
                AI agents are revolutionizing how financial institutions operate, from automated 
                trading to personalized customer service. Our platform brings this power to you.
              </p>
              
              <div className="space-y-4">
                {[
                  { icon: Zap, text: "Real-time market analysis and insights" },
                  { icon: Shield, text: "Enhanced fraud detection capabilities" },
                  { icon: BarChart3, text: "Data-driven investment decisions" }
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-none border border-border flex items-center justify-center">
                      <item.icon className="h-4 w-4 text-primary" />
                    </div>
                    <p className="font-body">{item.text}</p>
                  </div>
                ))}
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="relative"
            >
              <div className="aspect-square bg-gradient-to-br from-primary/10 to-secondary/10 rounded-none border border-border p-8 flex items-center justify-center">
                <div className="text-center">
                  <Bot className="h-24 w-24 mx-auto text-primary/20 mb-6" />
                  <p className="font-display text-2xl font-semibold mb-2">Obaid</p>
                  <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                    Your AI Financial Assistant
                  </p>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 md:py-32 px-6 md:px-12 lg:px-24">
        <div className="container mx-auto max-w-4xl text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display text-3xl md:text-5xl font-semibold tracking-tight mb-6">
              Ready to Explore?
            </h2>
            <p className="text-muted-foreground text-lg mb-10 max-w-2xl mx-auto">
              Dive into our comprehensive report on AI in finance or start a conversation 
              with Obaid for personalized financial insights.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button
                size="lg"
                onClick={() => navigate('/report')}
                className="font-mono uppercase tracking-wider text-sm h-14 px-8"
                data-testid="cta-report-btn"
              >
                Download Report
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={() => navigate('/chat')}
                className="font-mono uppercase tracking-wider text-sm h-14 px-8"
                data-testid="cta-chat-btn"
              >
                Chat with Obaid
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border">
        <div className="container mx-auto max-w-6xl flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="font-mono text-xs text-muted-foreground">
            © 2025 Finance AI Insights. Powered by OpenAI GPT-5.2
          </p>
          <p className="font-mono text-xs text-muted-foreground">
            Real-time data by Alpha Vantage
          </p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
