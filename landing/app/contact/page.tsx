"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ArrowRight, Check, Mail, MapPin, MessageSquare } from "lucide-react";
import Link from "next/link";

export default function ContactPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    company: "",
    message: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const pageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("[v0] Form submitted:", formData);
    setSubmitted(true);
    setTimeout(() => {
      setFormData({ name: "", email: "", company: "", message: "" });
      setSubmitted(false);
    }, 3000);
  };

  return (
    <div ref={pageRef} className="min-h-screen bg-background">
      {/* Navigation Bar */}
      <nav className="border-b border-foreground/10 sticky top-0 z-40 bg-background/80 backdrop-blur-sm">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-12 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 group">
            <span className="font-display text-xl text-foreground">SRE Copilot</span>
            <span className="font-mono text-xs text-muted-foreground">AI</span>
          </Link>
          <Link
            href="/"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            ← Back to home
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="py-16 lg:py-24 border-b border-foreground/10">
        <div className="max-w-3xl mx-auto px-6 lg:px-12">
          <div
            className={`transition-all duration-1000 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-display tracking-tight mb-6 leading-tight">
              Let&apos;s talk about
              <br />
              <span className="text-foreground/60">your cloud setup.</span>
            </h1>
            <p className="text-xl text-muted-foreground leading-relaxed max-w-2xl">
              Whether you are setting up a new Kubernetes cluster, registering Prometheus endpoints, or troubleshooting runbooks, we are here to support your team.
            </p>
          </div>
        </div>
      </section>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-6 lg:px-12 py-16 lg:py-24">
        <div className="grid lg:grid-cols-3 gap-12">
          {/* Contact Info */}
          <div
            className={`lg:col-span-1 transition-all duration-1000 delay-100 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            <h2 className="text-2xl font-display mb-8">Get in touch</h2>

            <div className="space-y-6">
              <div className="flex gap-4">
                <div className="bg-foreground/10 rounded-lg p-3 h-fit">
                  <Mail className="w-5 h-5 text-foreground" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground mb-1">Email</h3>
                  <a
                    href="mailto:support@srecopilot.ai"
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    support@srecopilot.ai
                  </a>
                </div>
              </div>

              <div className="flex gap-4">
                <div className="bg-foreground/10 rounded-lg p-3 h-fit">
                  <MessageSquare className="w-5 h-5 text-foreground" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground mb-1">Discord</h3>
                  <p className="text-muted-foreground">
                    Ask questions directly in our community server alerts channel
                  </p>
                </div>
              </div>

              <div className="flex gap-4">
                <div className="bg-foreground/10 rounded-lg p-3 h-fit">
                  <MapPin className="w-5 h-5 text-foreground" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground mb-1">Deployment</h3>
                  <p className="text-muted-foreground">Self-hosted agent or managed SaaS</p>
                </div>
              </div>
            </div>

            {/* Quick Links */}
            <div className="mt-12 pt-8 border-t border-foreground/10">
              <h3 className="text-sm font-semibold text-muted-foreground mb-4 uppercase tracking-wide">
                Quick Links
              </h3>
              <div className="space-y-3">
                <Link
                  href="/#features"
                  className="block text-foreground hover:text-foreground/70 transition-colors"
                >
                  View Features
                </Link>
                <Link
                  href="/#testimonials"
                  className="block text-foreground hover:text-foreground/70 transition-colors"
                >
                  Incident Scenarios
                </Link>
                <Link
                  href="/#how-it-works"
                  className="block text-foreground hover:text-foreground/70 transition-colors"
                >
                  System Workflow
                </Link>
              </div>
            </div>
          </div>

          {/* Contact Form */}
          <div
            className={`lg:col-span-2 transition-all duration-1000 delay-200 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
            }`}
          >
            {!submitted ? (
              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="grid sm:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Your Name
                    </label>
                    <Input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      placeholder="Jane Doe"
                      required
                      className="h-12 rounded-lg border-foreground/20"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-2">
                      Email Address
                    </label>
                    <Input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="jane@startup.com"
                      required
                      className="h-12 rounded-lg border-foreground/20"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Organization / Guild Name
                  </label>
                  <Input
                    type="text"
                    name="company"
                    value={formData.company}
                    onChange={handleChange}
                    placeholder="e.g. Acme DevOps"
                    className="h-12 rounded-lg border-foreground/20"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Tell us about your environment setup
                  </label>
                  <Textarea
                    name="message"
                    value={formData.message}
                    onChange={handleChange}
                    placeholder="What Kubernetes platform (e.g., EKS, GKE, local minikube) and Prometheus metric endpoints are you running? What incidents or alert loops are you targeting?"
                    required
                    rows={6}
                    className="rounded-lg border-foreground/20 resize-none"
                  />
                </div>

                <Button
                  type="submit"
                  size="lg"
                  className="w-full bg-foreground hover:bg-foreground/90 text-background h-12 rounded-lg text-base group"
                >
                  Send Message
                  <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
                </Button>

                <p className="text-xs text-muted-foreground text-center">
                  We typically respond within 24-48 hours
                </p>
              </form>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 px-8 bg-foreground/5 rounded-lg border border-foreground/10">
                <div className="bg-foreground/20 rounded-full p-4 mb-4">
                  <Check className="w-8 h-8 text-foreground" />
                </div>
                <h3 className="text-2xl font-display text-foreground mb-2">
                  Message received!
                </h3>
                <p className="text-muted-foreground text-center mb-8">
                  Thanks for reaching out. We&apos;ll review your message and get back to you soon at {formData.email}.
                </p>
                <Button
                  variant="outline"
                  onClick={() => (window.location.href = "/")}
                  className="border-foreground/20 rounded-full"
                >
                  Back to home
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer CTA */}
      <section className="border-t border-foreground/10 py-16 lg:py-24">
        <div className="max-w-3xl mx-auto px-6 lg:px-12 text-center">
          <h2 className="text-3xl md:text-4xl font-display mb-6">
            Ready to integrate?
          </h2>
          <p className="text-lg text-muted-foreground mb-8">
            Deploy the FastAPI SRE API and register your Discord bot with your clusters today. Check the installation docs on GitHub.
          </p>
          <a href="https://github.com/neutron420/SRE-Devops" target="_blank" rel="noopener noreferrer">
            <Button
              size="lg"
              className="bg-foreground hover:bg-foreground/90 text-background px-8 h-12 rounded-full"
            >
              Explore GitHub Repository
            </Button>
          </a>
        </div>
      </section>
    </div>
  );
}
