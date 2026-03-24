import { Footer } from "@/components/landing/footer";
import { Header } from "@/components/landing/header";
import { Hero } from "@/components/landing/hero";
import { SandboxSection } from "@/components/landing/sections/sandbox-section";
import { SkillsSection } from "@/components/landing/sections/skills-section";

export default function LandingPage() {
  return (
    <div className="min-h-screen w-full bg-[#0a0a0a]">
      <Header />
      <main className="flex w-full flex-col">
        <Hero />
        <SkillsSection />
        <SandboxSection />
      </main>
      <Footer />
    </div>
  );
}
