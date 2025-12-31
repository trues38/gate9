# G9 Component Library

React + Tailwind CSS 기반 컴포넌트 코드 레퍼런스.

## UI Components

### GlowButton

```jsx
const GlowButton = ({ children, variant = 'cyan', size = 'lg', ...props }) => {
  const variants = {
    cyan: 'bg-cyan-500 hover:bg-cyan-400 shadow-[0_0_30px_rgba(0,245,255,0.4)]',
    purple: 'bg-purple-500 hover:bg-purple-400 shadow-[0_0_30px_rgba(168,85,247,0.4)]',
    gradient: 'bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-400 hover:to-purple-400',
  };
  
  const sizes = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg',
  };

  return (
    <button
      className={`
        ${variants[variant]} ${sizes[size]}
        font-semibold rounded-lg text-white
        transition-all duration-300
        hover:scale-105 hover:shadow-[0_0_40px_rgba(0,245,255,0.5)]
        active:scale-95
      `}
      {...props}
    >
      {children}
    </button>
  );
};
```

### OutlineButton

```jsx
const OutlineButton = ({ children, ...props }) => (
  <button
    className="
      px-8 py-4 text-lg font-semibold rounded-lg
      border border-slate-600 text-slate-300
      hover:border-cyan-500 hover:text-cyan-400
      transition-all duration-300
      hover:shadow-[0_0_20px_rgba(0,245,255,0.2)]
    "
    {...props}
  >
    {children}
  </button>
);
```

### FeatureCard

```jsx
const FeatureCard = ({ icon, title, description, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ duration: 0.5, delay }}
    className="
      group p-6 rounded-2xl
      bg-gradient-to-b from-slate-800/50 to-slate-900/50
      border border-slate-700/50
      hover:border-cyan-500/50
      transition-all duration-300
      hover:shadow-[0_0_30px_rgba(0,245,255,0.1)]
    "
  >
    <div className="
      w-12 h-12 rounded-lg mb-4
      bg-gradient-to-br from-cyan-500/20 to-purple-500/20
      flex items-center justify-center text-2xl
      group-hover:scale-110 transition-transform
    ">
      {icon}
    </div>
    <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
    <p className="text-slate-400 leading-relaxed">{description}</p>
  </motion.div>
);
```

### PricingCard

```jsx
const PricingCard = ({ tier, price, features, featured = false }) => (
  <div className={`
    relative p-8 rounded-2xl
    ${featured 
      ? 'bg-gradient-to-b from-cyan-500/10 to-purple-500/10 border-2 border-cyan-500/50 scale-105' 
      : 'bg-slate-800/50 border border-slate-700/50'
    }
  `}>
    {featured && (
      <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full text-sm font-semibold">
        MOST POPULAR
      </div>
    )}
    
    <h3 className="text-xl font-semibold text-slate-300">{tier}</h3>
    
    <div className="mt-4 mb-6">
      <span className="text-5xl font-bold text-white" style={{ fontFamily: 'Orbitron' }}>
        ${price}
      </span>
      <span className="text-slate-400">/month</span>
    </div>
    
    <ul className="space-y-3 mb-8">
      {features.map((feature, i) => (
        <li key={i} className="flex items-center gap-2 text-slate-300">
          <span className="text-cyan-400">✓</span> {feature}
        </li>
      ))}
    </ul>
    
    <GlowButton variant={featured ? 'gradient' : 'cyan'} className="w-full">
      Get Started
    </GlowButton>
  </div>
);
```

### DataCard (실시간 데이터 표시)

```jsx
const DataCard = ({ label, value, change, trend }) => (
  <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/50">
    <p className="text-sm text-slate-400 mb-1">{label}</p>
    <p className="text-2xl font-bold text-white" style={{ fontFamily: 'JetBrains Mono' }}>
      {value}
    </p>
    {change && (
      <p className={`text-sm mt-1 ${trend === 'up' ? 'text-green-400' : 'text-red-400'}`}>
        {trend === 'up' ? '↑' : '↓'} {change}
      </p>
    )}
  </div>
);
```

### SectionHeader

```jsx
const SectionHeader = ({ title, subtitle, align = 'center' }) => (
  <div className={`mb-16 ${align === 'center' ? 'text-center' : ''}`}>
    <h2 
      className="text-4xl md:text-5xl font-bold text-white mb-4"
      style={{ fontFamily: 'Space Grotesk' }}
    >
      {title}
    </h2>
    {subtitle && (
      <p className="text-xl text-slate-400 max-w-2xl mx-auto">
        {subtitle}
      </p>
    )}
  </div>
);
```

## Section Components

### Hero Section

```jsx
const HeroSection = () => (
  <section className="relative min-h-screen flex items-center overflow-hidden">
    {/* Background Effects */}
    <GridBackground />
    <GradientOrbs />
    
    <div className="relative z-10 container mx-auto px-6">
      <div className="grid lg:grid-cols-2 gap-12 items-center">
        {/* Left: Content */}
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
        >
          <div className="inline-block px-4 py-2 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-sm mb-6">
            🚀 AI-Powered Analytics Platform
          </div>
          
          <h1 
            className="text-5xl md:text-7xl font-bold leading-tight"
            style={{ fontFamily: 'Orbitron' }}
          >
            <span className="text-white">Unlock the</span>
            <br />
            <span className="bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">
              Power of Data
            </span>
          </h1>
          
          <p className="text-xl text-slate-400 mt-6 max-w-lg">
            Advanced analytics engine that transforms complex data into actionable insights in real-time.
          </p>
          
          <div className="flex flex-wrap gap-4 mt-10">
            <GlowButton>Start Free Trial</GlowButton>
            <OutlineButton>Watch Demo →</OutlineButton>
          </div>
          
          {/* Trust indicators */}
          <div className="flex items-center gap-8 mt-12 text-slate-500">
            <span>Trusted by</span>
            <span className="text-white font-semibold">1,000+</span>
            <span>professionals</span>
          </div>
        </motion.div>
        
        {/* Right: Dashboard Preview */}
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="relative"
        >
          <DashboardMockup />
        </motion.div>
      </div>
    </div>
  </section>
);
```

### Features Section

```jsx
const FeaturesSection = () => {
  const features = [
    { icon: '⚡', title: 'Real-time Analysis', description: 'Process millions of data points in milliseconds' },
    { icon: '🎯', title: 'Smart Predictions', description: 'AI-powered forecasting with 95%+ accuracy' },
    { icon: '📊', title: 'Visual Insights', description: 'Interactive dashboards and custom reports' },
    { icon: '🔒', title: 'Enterprise Security', description: 'Bank-grade encryption and compliance' },
    { icon: '🔗', title: 'API Integration', description: 'Connect with 100+ data sources' },
    { icon: '💬', title: '24/7 Support', description: 'Dedicated team for your success' },
  ];

  return (
    <section className="py-24 bg-slate-950">
      <div className="container mx-auto px-6">
        <SectionHeader 
          title="Powerful Features"
          subtitle="Everything you need to make data-driven decisions"
        />
        
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <FeatureCard key={i} {...feature} delay={i * 0.1} />
          ))}
        </div>
      </div>
    </section>
  );
};
```

### Pricing Section

```jsx
const PricingSection = () => {
  const plans = [
    {
      tier: 'Starter',
      price: '49',
      features: ['5 Projects', 'Basic Analytics', 'Email Support', '1GB Storage'],
    },
    {
      tier: 'Pro',
      price: '149',
      features: ['Unlimited Projects', 'Advanced Analytics', 'Priority Support', '50GB Storage', 'API Access'],
      featured: true,
    },
    {
      tier: 'Enterprise',
      price: 'Custom',
      features: ['Everything in Pro', 'Dedicated Account Manager', 'Custom Integrations', 'SLA Guarantee'],
    },
  ];

  return (
    <section className="py-24 bg-gradient-to-b from-slate-950 to-slate-900">
      <div className="container mx-auto px-6">
        <SectionHeader 
          title="Simple Pricing"
          subtitle="Start free, scale as you grow"
        />
        
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {plans.map((plan, i) => (
            <PricingCard key={i} {...plan} />
          ))}
        </div>
      </div>
    </section>
  );
};
```

### CTA Section

```jsx
const CTASection = () => (
  <section className="py-24 relative overflow-hidden">
    <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 to-purple-500/10" />
    
    <div className="container mx-auto px-6 text-center relative z-10">
      <h2 
        className="text-4xl md:text-5xl font-bold text-white mb-6"
        style={{ fontFamily: 'Space Grotesk' }}
      >
        Ready to Transform Your Data?
      </h2>
      <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto">
        Join thousands of professionals making smarter decisions with G9 Engine.
      </p>
      <GlowButton variant="gradient" size="lg">
        Start Your Free Trial →
      </GlowButton>
    </div>
  </section>
);
```

### Footer

```jsx
const Footer = () => (
  <footer className="py-12 bg-slate-950 border-t border-slate-800">
    <div className="container mx-auto px-6">
      <div className="grid md:grid-cols-4 gap-8">
        <div>
          <h3 className="text-xl font-bold text-white mb-4" style={{ fontFamily: 'Orbitron' }}>
            G9 Engine
          </h3>
          <p className="text-slate-400">
            AI-powered analytics for smarter decisions.
          </p>
        </div>
        
        <div>
          <h4 className="font-semibold text-white mb-4">Product</h4>
          <ul className="space-y-2 text-slate-400">
            <li><a href="#" className="hover:text-cyan-400 transition">Features</a></li>
            <li><a href="#" className="hover:text-cyan-400 transition">Pricing</a></li>
            <li><a href="#" className="hover:text-cyan-400 transition">API Docs</a></li>
          </ul>
        </div>
        
        <div>
          <h4 className="font-semibold text-white mb-4">Company</h4>
          <ul className="space-y-2 text-slate-400">
            <li><a href="#" className="hover:text-cyan-400 transition">About</a></li>
            <li><a href="#" className="hover:text-cyan-400 transition">Blog</a></li>
            <li><a href="#" className="hover:text-cyan-400 transition">Careers</a></li>
          </ul>
        </div>
        
        <div>
          <h4 className="font-semibold text-white mb-4">Legal</h4>
          <ul className="space-y-2 text-slate-400">
            <li><a href="#" className="hover:text-cyan-400 transition">Privacy</a></li>
            <li><a href="#" className="hover:text-cyan-400 transition">Terms</a></li>
          </ul>
        </div>
      </div>
      
      <div className="mt-12 pt-8 border-t border-slate-800 text-center text-slate-500">
        © 2024 G9 Engine. All rights reserved.
      </div>
    </div>
  </footer>
);
```
