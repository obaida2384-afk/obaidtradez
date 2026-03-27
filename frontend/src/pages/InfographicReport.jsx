import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { 
  Download, 
  ChevronLeft, 
  ChevronRight,
  TrendingUp,
  Users,
  DollarSign,
  Clock,
  AlertTriangle,
  CheckCircle,
  Globe
} from "lucide-react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Area,
  AreaChart
} from "recharts";
import axios from "axios";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COLORS = ['#044738', '#D4AF37', '#10B981', '#F97316', '#3B82F6'];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-background/95 backdrop-blur border border-border px-4 py-3 shadow-xl">
        <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} className="font-mono text-sm font-semibold" style={{ color: entry.color }}>
            {entry.name}: {entry.value}{typeof entry.value === 'number' && entry.value < 100 ? '%' : ''}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

const InfographicReport = () => {
  const [data, setData] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const reportRef = useRef(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const response = await axios.get(`${API}/infographic/data`);
      setData(response.data);
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Failed to load report data");
    } finally {
      setIsLoading(false);
    }
  };

  const exportToPDF = async () => {
    if (!reportRef.current) return;
    
    setIsExporting(true);
    toast.info("Generating PDF...");
    
    try {
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      
      for (let page = 1; page <= 3; page++) {
        setCurrentPage(page);
        await new Promise(resolve => setTimeout(resolve, 500));
        
        const canvas = await html2canvas(reportRef.current, {
          scale: 2,
          useCORS: true,
          logging: false,
          backgroundColor: '#ffffff'
        });
        
        const imgData = canvas.toDataURL('image/jpeg', 0.95);
        const imgWidth = pageWidth - 20;
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        
        if (page > 1) pdf.addPage();
        pdf.addImage(imgData, 'JPEG', 10, 10, imgWidth, Math.min(imgHeight, pageHeight - 20));
      }
      
      pdf.save('AI-in-Finance-Report-2025.pdf');
      toast.success("PDF downloaded successfully!");
    } catch (error) {
      console.error("PDF export error:", error);
      toast.error("Failed to generate PDF");
    } finally {
      setIsExporting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" data-testid="report-loading">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="font-mono text-sm text-muted-foreground">Loading report data...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Failed to load report data</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen pt-20 pb-12 px-6 md:px-12" data-testid="infographic-report">
      {/* Controls */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 bg-background/95 backdrop-blur border border-border px-6 py-3 shadow-xl no-print">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
          disabled={currentPage === 1}
          data-testid="prev-page-btn"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        
        <div className="flex items-center gap-2">
          {[1, 2, 3].map(page => (
            <button
              key={page}
              onClick={() => setCurrentPage(page)}
              className={`w-8 h-8 font-mono text-sm transition-all ${
                currentPage === page 
                  ? 'bg-primary text-primary-foreground' 
                  : 'bg-muted hover:bg-muted/80'
              }`}
              data-testid={`page-${page}-btn`}
            >
              {page}
            </button>
          ))}
        </div>
        
        <Button
          variant="outline"
          size="icon"
          onClick={() => setCurrentPage(p => Math.min(3, p + 1))}
          disabled={currentPage === 3}
          data-testid="next-page-btn"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        
        <div className="w-px h-8 bg-border mx-2" />
        
        <Button
          onClick={exportToPDF}
          disabled={isExporting}
          className="font-mono text-xs uppercase tracking-wider"
          data-testid="export-pdf-btn"
        >
          <Download className="h-4 w-4 mr-2" />
          {isExporting ? 'Exporting...' : 'Export PDF'}
        </Button>
      </div>

      {/* Report Content */}
      <div ref={reportRef} className="max-w-6xl mx-auto print-container">
        {currentPage === 1 && <Page1 data={data.page1} />}
        {currentPage === 2 && <Page2 data={data.page2} />}
        {currentPage === 3 && <Page3 data={data.page3} />}
      </div>
    </div>
  );
};

// Page 1: The Landscape
const Page1 = ({ data }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="space-y-8"
  >
    {/* Header */}
    <div className="text-center mb-12">
      <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground mb-4">
        Page 1 of 3 • {data.year}
      </p>
      <h1 className="font-display text-4xl md:text-5xl font-bold tracking-tight mb-4">
        {data.title}
      </h1>
      <p className="text-muted-foreground max-w-2xl mx-auto">
        A comprehensive overview of AI adoption across the financial services industry
      </p>
    </div>

    {/* Key Stats */}
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {data.key_stats.map((stat, i) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.1 }}
          className="stat-card bento-item text-center"
        >
          <p className="font-mono text-3xl md:text-4xl font-bold text-primary mb-2">
            {stat.value}
          </p>
          <p className="font-mono text-xs uppercase tracking-wider font-semibold mb-1">
            {stat.label}
          </p>
          <p className="text-xs text-muted-foreground">{stat.description}</p>
        </motion.div>
      ))}
    </div>

    {/* Charts Row */}
    <div className="grid md:grid-cols-2 gap-6">
      {/* Adoption by Sector */}
      <Card className="bento-item">
        <h3 className="font-display text-lg font-semibold mb-6">AI Adoption by Sector</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.adoption_by_sector} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fontFamily: 'JetBrains Mono' }} />
              <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 11, fontFamily: 'Inter' }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="value" fill="hsl(var(--primary))" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Use Cases Pie */}
      <Card className="bento-item">
        <h3 className="font-display text-lg font-semibold mb-6">Top AI Use Cases</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data.use_cases}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                dataKey="percentage"
                nameKey="name"
                label={({ name, percentage }) => `${percentage}%`}
                labelLine={false}
              >
                {data.use_cases.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend 
                formatter={(value) => <span className="text-xs font-body">{value}</span>}
                layout="vertical"
                align="right"
                verticalAlign="middle"
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>

    {/* Use Cases Table */}
    <Card className="bento-item overflow-hidden">
      <h3 className="font-display text-lg font-semibold mb-6">Primary AI Applications in Finance</h3>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Use Case</th>
              <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Adoption</th>
              <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Description</th>
            </tr>
          </thead>
          <tbody>
            {data.use_cases.map((item, i) => (
              <tr key={item.name} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                <td className="py-3 px-4 font-semibold">{item.name}</td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden max-w-32">
                      <div 
                        className="h-full rounded-full transition-all duration-500"
                        style={{ width: `${item.percentage}%`, backgroundColor: COLORS[i % COLORS.length] }}
                      />
                    </div>
                    <span className="font-mono text-sm">{item.percentage}%</span>
                  </div>
                </td>
                <td className="py-3 px-4 text-muted-foreground text-sm">{item.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  </motion.div>
);

// Page 2: Adoption Velocity
const Page2 = ({ data }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="space-y-8"
  >
    {/* Header */}
    <div className="text-center mb-12">
      <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground mb-4">
        Page 2 of 3
      </p>
      <h1 className="font-display text-4xl md:text-5xl font-bold tracking-tight mb-4">
        {data.title}
      </h1>
      <p className="text-muted-foreground max-w-2xl mx-auto">
        Tracking the rapid acceleration of AI adoption across financial institutions
      </p>
    </div>

    {/* Timeline Chart */}
    <Card className="bento-item">
      <h3 className="font-display text-lg font-semibold mb-6">AI Adoption Timeline (2020-2025)</h3>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data.adoption_timeline}>
            <defs>
              <linearGradient id="adoptionGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="year" tick={{ fontSize: 12, fontFamily: 'JetBrains Mono' }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 12, fontFamily: 'JetBrains Mono' }} />
            <Tooltip content={<CustomTooltip />} />
            <Area 
              type="monotone" 
              dataKey="adoption" 
              stroke="hsl(var(--primary))" 
              strokeWidth={2}
              fill="url(#adoptionGradient)"
              name="Adoption Rate"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>

    {/* Investment & Challenges */}
    <div className="grid md:grid-cols-2 gap-6">
      {/* Investment Breakdown */}
      <Card className="bento-item">
        <h3 className="font-display text-lg font-semibold mb-6">Investment Breakdown ($B)</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data.investment_breakdown}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="amount"
                nameKey="category"
                label={({ category, amount }) => `$${amount}B`}
              >
                {data.investment_breakdown.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend 
                formatter={(value) => <span className="text-xs font-body">{value}</span>}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Implementation Challenges */}
      <Card className="bento-item">
        <h3 className="font-display text-lg font-semibold mb-6">Implementation Challenges</h3>
        <div className="space-y-4">
          {data.implementation_challenges.map((item, i) => (
            <div key={item.challenge} className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm font-medium">{item.challenge}</span>
                <span className="font-mono text-sm text-muted-foreground">{item.severity}%</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${item.severity}%` }}
                  transition={{ delay: i * 0.1, duration: 0.5 }}
                  className="h-full rounded-full"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                />
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>

    {/* Regional Adoption */}
    <Card className="bento-item">
      <h3 className="font-display text-lg font-semibold mb-6 flex items-center gap-2">
        <Globe className="h-5 w-5 text-primary" />
        Regional AI Adoption Rates
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {data.regional_adoption.map((region, i) => (
          <motion.div
            key={region.region}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.1 }}
            className="text-center p-4 border border-border hover:border-primary/50 transition-colors"
          >
            <p className="font-mono text-2xl font-bold text-primary mb-2">{region.percentage}%</p>
            <p className="text-xs text-muted-foreground">{region.region}</p>
          </motion.div>
        ))}
      </div>
    </Card>

    {/* Key Insights */}
    <div className="grid md:grid-cols-3 gap-4">
      <Card className="bento-item flex items-center gap-4">
        <div className="h-12 w-12 rounded-none border border-border flex items-center justify-center shrink-0">
          <TrendingUp className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Growth Rate</p>
          <p className="font-display text-xl font-semibold">+149%</p>
          <p className="text-xs text-muted-foreground">Since 2020</p>
        </div>
      </Card>
      <Card className="bento-item flex items-center gap-4">
        <div className="h-12 w-12 rounded-none border border-border flex items-center justify-center shrink-0">
          <DollarSign className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Total Investment</p>
          <p className="font-display text-xl font-semibold">$35B</p>
          <p className="text-xs text-muted-foreground">Annual Spending</p>
        </div>
      </Card>
      <Card className="bento-item flex items-center gap-4">
        <div className="h-12 w-12 rounded-none border border-border flex items-center justify-center shrink-0">
          <Users className="h-5 w-5 text-primary" />
        </div>
        <div>
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Firms Adopting</p>
          <p className="font-display text-xl font-semibold">73%</p>
          <p className="text-xs text-muted-foreground">Of Major Institutions</p>
        </div>
      </Card>
    </div>
  </motion.div>
);

// Page 3: Future Projections
const Page3 = ({ data }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="space-y-8"
  >
    {/* Header */}
    <div className="text-center mb-12">
      <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground mb-4">
        Page 3 of 3
      </p>
      <h1 className="font-display text-4xl md:text-5xl font-bold tracking-tight mb-4">
        {data.title}
      </h1>
      <p className="text-muted-foreground max-w-2xl mx-auto">
        Market forecasts and strategic recommendations for AI implementation
      </p>
    </div>

    {/* Market Forecast */}
    <Card className="bento-item">
      <h3 className="font-display text-lg font-semibold mb-6">AI in Finance Market Forecast ($B)</h3>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.market_forecast}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="year" tick={{ fontSize: 12, fontFamily: 'JetBrains Mono' }} />
            <YAxis tick={{ fontSize: 12, fontFamily: 'JetBrains Mono' }} />
            <Tooltip content={<CustomTooltip />} />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke="hsl(var(--primary))" 
              strokeWidth={3}
              dot={{ fill: 'hsl(var(--primary))', strokeWidth: 2, r: 5 }}
              name="Market Size ($B)"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>

    {/* Emerging Trends Table */}
    <Card className="bento-item overflow-hidden">
      <h3 className="font-display text-lg font-semibold mb-6">Emerging AI Trends in Finance</h3>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Trend</th>
              <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Impact</th>
              <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Timeline</th>
            </tr>
          </thead>
          <tbody>
            {data.emerging_trends.map((trend) => (
              <tr key={trend.trend} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                <td className="py-3 px-4 font-medium">{trend.trend}</td>
                <td className="py-3 px-4">
                  <span className={`inline-flex items-center px-2 py-1 text-xs font-mono uppercase tracking-wider ${
                    trend.impact === 'Very High' ? 'bg-primary/20 text-primary' :
                    trend.impact === 'High' ? 'bg-secondary/20 text-secondary-foreground' :
                    'bg-muted text-muted-foreground'
                  }`}>
                    {trend.impact}
                  </span>
                </td>
                <td className="py-3 px-4 font-mono text-sm text-muted-foreground">{trend.timeline}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>

    {/* Job Impact */}
    <Card className="bento-item">
      <h3 className="font-display text-lg font-semibold mb-6">AI Impact on Jobs in Finance</h3>
      <div className="grid md:grid-cols-3 gap-6">
        <div className="text-center p-6 border border-border">
          <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-3" />
          <p className="font-mono text-2xl font-bold text-green-500 mb-1">
            +{(data.job_impact.created / 1000000).toFixed(1)}M
          </p>
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Jobs Created</p>
        </div>
        <div className="text-center p-6 border border-border">
          <TrendingUp className="h-8 w-8 text-primary mx-auto mb-3" />
          <p className="font-mono text-2xl font-bold text-primary mb-1">
            {(data.job_impact.transformed / 1000000).toFixed(1)}M
          </p>
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Jobs Transformed</p>
        </div>
        <div className="text-center p-6 border border-border">
          <AlertTriangle className="h-8 w-8 text-orange-500 mx-auto mb-3" />
          <p className="font-mono text-2xl font-bold text-orange-500 mb-1">
            {(data.job_impact.automated / 1000000).toFixed(1)}M
          </p>
          <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Jobs Automated</p>
        </div>
      </div>
    </Card>

    {/* Benefits & Cautions */}
    <div className="grid md:grid-cols-2 gap-6">
      <Card className="bento-item">
        <h3 className="font-display text-lg font-semibold mb-6 flex items-center gap-2">
          <CheckCircle className="h-5 w-5 text-green-500" />
          Key Benefits
        </h3>
        <ul className="space-y-3">
          {data.benefits.map((benefit, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="h-5 w-5 rounded-full bg-green-500/10 text-green-500 flex items-center justify-center text-xs font-mono shrink-0 mt-0.5">
                {i + 1}
              </span>
              <span className="text-sm leading-relaxed">{benefit}</span>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="bento-item">
        <h3 className="font-display text-lg font-semibold mb-6 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-orange-500" />
          Cautionary Notes
        </h3>
        <ul className="space-y-3">
          {data.cautions.map((caution, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="h-5 w-5 rounded-full bg-orange-500/10 text-orange-500 flex items-center justify-center text-xs font-mono shrink-0 mt-0.5">
                !
              </span>
              <span className="text-sm leading-relaxed">{caution}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>

    {/* Recommendations */}
    <Card className="bento-item">
      <h3 className="font-display text-lg font-semibold mb-6">Strategic Recommendations</h3>
      <div className="grid md:grid-cols-5 gap-4">
        {data.recommendations.map((rec, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="p-4 border border-border hover:border-primary/50 transition-colors"
          >
            <div className="h-8 w-8 rounded-none bg-primary/10 text-primary flex items-center justify-center font-mono text-sm font-bold mb-3">
              {i + 1}
            </div>
            <p className="text-sm leading-relaxed">{rec}</p>
          </motion.div>
        ))}
      </div>
    </Card>

    {/* Footer */}
    <div className="text-center pt-8 border-t border-border">
      <p className="font-mono text-xs text-muted-foreground">
        Report Generated: January 2025 • Data Sources: Industry Reports, Market Research, Company Filings
      </p>
    </div>
  </motion.div>
);

export default InfographicReport;
