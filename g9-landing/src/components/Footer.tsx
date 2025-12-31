'use client';

export default function Footer() {
  return (
    <footer className="py-12 bg-[#0a0f1a] border-t border-slate-800">
      <div className="container mx-auto px-6">
        <div className="grid md:grid-cols-4 gap-8">
          <div>
            <h3
              className="text-xl font-bold text-white mb-4"
              style={{ fontFamily: 'Orbitron, sans-serif' }}
            >
              G9 Intelligence
            </h3>
            <p className="text-slate-400">
              AI-powered analytics for smarter decisions in sports and economics.
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-white mb-4">Products</h4>
            <ul className="space-y-2 text-slate-400">
              <li>
                <a href="#" className="hover:text-cyan-400 transition">
                  G9-Sport
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-cyan-400 transition">
                  G9-Economy
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-cyan-400 transition">
                  API Access
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-cyan-400 transition">
                  Enterprise
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-white mb-4">Resources</h4>
            <ul className="space-y-2 text-slate-400">
              <li>
                <a href="#" className="hover:text-cyan-400 transition">
                  Documentation
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-cyan-400 transition">
                  Blog
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-cyan-400 transition">
                  Case Studies
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-cyan-400 transition">
                  Tutorials
                </a>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-white mb-4">Company</h4>
            <ul className="space-y-2 text-slate-400">
              <li>
                <a href="#" className="hover:text-cyan-400 transition">
                  About
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-cyan-400 transition">
                  Careers
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-cyan-400 transition">
                  Privacy Policy
                </a>
              </li>
              <li>
                <a href="#" className="hover:text-cyan-400 transition">
                  Terms of Service
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 pt-8 border-t border-slate-800 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="text-slate-500 text-sm">
            © 2025 G9 Intelligence DataLabs. All rights reserved.
          </div>
          <div className="flex gap-6">
            <a href="#" className="text-slate-500 hover:text-cyan-400 transition">
              Twitter
            </a>
            <a href="#" className="text-slate-500 hover:text-cyan-400 transition">
              LinkedIn
            </a>
            <a href="#" className="text-slate-500 hover:text-cyan-400 transition">
              GitHub
            </a>
            <a href="#" className="text-slate-500 hover:text-cyan-400 transition">
              Discord
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
