"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Menu, X, Github } from "lucide-react";

const navLinks = [
  { name: "Features",  href: "#features"      },
  { name: "Workflow",  href: "#how-it-works"  },
  { name: "Scenarios", href: "#testimonials"  },
  { name: "AI Agents", href: "#developers"    },
  { name: "Get Started", href: "#cta"         },
];

export function Navigation() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header
      className={`fixed z-50 transition-all duration-500 ${
        isScrolled 
          ? "top-4 left-4 right-4" 
          : "top-0 left-0 right-0"
      }`}
    >
      <nav 
        className={`mx-auto transition-all duration-500 ${
          isScrolled || isMobileMenuOpen
            ? "bg-background/80 backdrop-blur-xl border border-foreground/10 rounded-2xl shadow-lg max-w-[1200px]"
            : "bg-transparent max-w-[1400px]"
        }`}
      >
        <div 
          className={`flex items-center justify-between transition-all duration-500 px-6 lg:px-8 ${
            isScrolled ? "h-14" : "h-20"
          }`}
        >
          {/* Logo */}
          <a href="#" className="flex items-center gap-2 group">
            <span className={`font-display tracking-tight transition-all duration-500 ${isScrolled ? "text-xl text-foreground" : "text-2xl text-white"}`}>SRE Copilot</span>
            <span className={`font-mono transition-all duration-500 ${isScrolled ? "text-[10px] mt-0.5 text-muted-foreground" : "text-xs mt-1 text-white/60"}`}></span>
          </a>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-12">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                className={`text-sm transition-colors duration-300 relative group ${isScrolled ? "text-foreground/70 hover:text-foreground" : "text-white/70 hover:text-white"}`}
              >
                {link.name}
                <span className={`absolute -bottom-1 left-0 w-0 h-px transition-all duration-300 group-hover:w-full ${isScrolled ? "bg-foreground" : "bg-white"}`} />
              </a>
            ))}
          </div>

          {/* Desktop CTA */}
          <div className="hidden md:flex items-center gap-6">
            <a 
              href="https://github.com/neutron420/SRE-Devops" 
              target="_blank" 
              rel="noopener noreferrer"
              className={`inline-flex items-center gap-1.5 transition-all duration-300 ${
                isScrolled ? "text-xs text-foreground/75 hover:text-foreground" : "text-sm text-white/75 hover:text-white"
              }`}
            >
              <Github className="w-4 h-4" />
              <span>GitHub</span>
            </a>
            <a 
              href="https://discord.gg/VTf2Tszhg" 
              target="_blank" 
              rel="noopener noreferrer"
              className={`inline-flex items-center gap-1.5 transition-all duration-300 ${
                isScrolled ? "text-xs text-foreground/75 hover:text-foreground" : "text-sm text-white/75 hover:text-white"
              }`}
            >
              <svg viewBox="0 0 127.14 96.36" className="w-4 h-4 fill-current">
                <path d="M107.7,8.07A105.15,105.15,0,0,0,77.26,0a77.19,77.19,0,0,0-3.3,6.83A96.67,96.67,0,0,0,52.22,6.83,77.19,77.19,0,0,0,48.92,0,105.15,105.15,0,0,0,18.48,8.07C3.6,30.12-2.19,51.65.69,72.67a105.09,105.09,0,0,0,32.22,16.29,80.06,80.06,0,0,0,6.77-11A68.6,68.6,0,0,1,28.84,72.2c1,.78,2.1,1.53,3.09,2.24a74.62,74.62,0,0,0,70.52,0c1-.71,2.05-1.46,3.09-2.24a68.86,68.86,0,0,1-10.84,5.77,80.06,80.06,0,0,0,6.77,11,105.09,105.09,0,0,0,32.22-16.29C130.66,45.55,124.62,24.23,107.7,8.07ZM42.45,60.83c-6.39,0-11.66-5.83-11.66-13s5.17-13,11.66-13,11.72,5.88,11.66,13S48.84,60.83,42.45,60.83Zm42.4,0c-6.39,0-11.66-5.83-11.66-13s5.17-13,11.66-13,11.72,5.88,11.66,13S91.24,60.83,84.85,60.83Z"/>
              </svg>
              <span>Discord</span>
            </a>
            <Button
              size="sm"
              className={`rounded-full transition-all duration-500 ${isScrolled ? "bg-foreground hover:bg-foreground/90 text-background px-4 h-8 text-xs" : "bg-white hover:bg-white/90 text-black px-6"}`}
              asChild
            >
              <a 
                href="https://discord.com/oauth2/authorize?client_id=1515334758505119927&permissions=3230976&scope=bot%20applications.commands" 
                target="_blank" 
                rel="noopener noreferrer"
              >
                Invite Bot
              </a>
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className={`md:hidden p-2 transition-colors duration-500 ${isScrolled || isMobileMenuOpen ? "text-foreground" : "text-white"}`}
            aria-label="Toggle menu"
          >
            {isMobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>

      </nav>
      
      {/* Mobile Menu - Full Screen Overlay */}
      <div
        className={`md:hidden fixed inset-0 bg-background z-40 transition-all duration-500 ${
          isMobileMenuOpen 
            ? "opacity-100 pointer-events-auto" 
            : "opacity-0 pointer-events-none"
        }`}
        style={{ top: 0 }}
      >
        <div className="flex flex-col h-full px-8 pt-28 pb-8">
          {/* Navigation Links */}
          <div className="flex-1 flex flex-col justify-center gap-8">
            {navLinks.map((link, i) => (
              <a
                key={link.name}
                href={link.href}
                onClick={() => setIsMobileMenuOpen(false)}
                className={`text-5xl font-display text-foreground hover:text-muted-foreground transition-all duration-500 ${
                  isMobileMenuOpen 
                    ? "opacity-100 translate-y-0" 
                    : "opacity-0 translate-y-4"
                }`}
                style={{ transitionDelay: isMobileMenuOpen ? `${i * 75}ms` : "0ms" }}
              >
                {link.name}
              </a>
            ))}
          </div>
          
          {/* Bottom CTAs */}
          <div className={`flex gap-4 pt-8 border-t border-foreground/10 transition-all duration-500 ${
            isMobileMenuOpen 
              ? "opacity-100 translate-y-0" 
              : "opacity-0 translate-y-4"
          }`}
          style={{ transitionDelay: isMobileMenuOpen ? "300ms" : "0ms" }}
          >
            <Button
              variant="outline"
              className="flex-1 rounded-full h-14 text-base border-foreground/20"
              onClick={() => setIsMobileMenuOpen(false)}
              asChild
            >
              <a href="#cta">Get in touch</a>
            </Button>
            <Button
              className="flex-1 bg-foreground text-background rounded-full h-14 text-base"
              onClick={() => setIsMobileMenuOpen(false)}
              asChild
            >
              <a href="#cta">Book a call</a>
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
