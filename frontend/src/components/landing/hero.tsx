"use client";

import { ChevronRightIcon } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";

import { AuroraText } from "@/components/ui/aurora-text";
import { Button } from "@/components/ui/button";
import Galaxy from "@/components/ui/galaxy";
import { WordRotate } from "@/components/ui/word-rotate";
import { cn } from "@/lib/utils";

export function Hero({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex size-full flex-col items-center justify-center",
        className,
      )}
    >
      {/* Deep space background — subtle, slow, low density */}
      <div className="absolute inset-0 z-0 bg-black/60">
        <Galaxy
          mouseRepulsion={false}
          starSpeed={0.1}
          density={0.35}
          glowIntensity={0.2}
          twinkleIntensity={0.4}
          speed={0.3}
          saturation={0.3}
          hueShift={220}
        />
      </div>

      <div className="container-md relative z-10 mx-auto flex h-screen flex-col items-center justify-center">
        {/* Brand name with aurora gradient */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        >
          <h1 className="text-center text-6xl font-bold tracking-tight md:text-8xl">
            <AuroraText
              colors={["#60a5fa", "#a78bfa", "#818cf8", "#38bdf8"]}
              speed={0.6}
            >
              Allo
            </AuroraText>
          </h1>
          <p className="mt-2 text-center font-serif text-2xl tracking-widest text-white/50 md:text-3xl">
            元枢
          </p>
        </motion.div>

        {/* Capability rotation */}
        <motion.div
          className="mt-8 flex items-center gap-3 text-3xl font-bold md:text-5xl"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
        >
          <WordRotate
            words={[
              "Deep Research",
              "Collect Data",
              "Analyze Data",
              "Generate Webpages",
              "Vibe Coding",
              "Generate Slides",
              "Generate Images",
              "Generate Podcasts",
              "Generate Videos",
              "Organize Emails",
              "Do Anything",
              "Learn Anything",
            ]}
          />
          <span className="text-white/60">with Allo</span>
        </motion.div>

        {/* Tagline in Chinese */}
        <motion.p
          className="mt-8 max-w-2xl text-center text-lg leading-relaxed md:text-xl"
          style={{ color: "rgb(160,160,170)" }}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
        >
          你的 AI 办公助手 — 调研、编程、分析、创作，
          <br />
          从几分钟到几小时的任务，元枢帮你搞定。
        </motion.p>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.6, ease: "easeOut" }}
        >
          <Link href="/workspace">
            <Button
              className="mt-10 border-white/10 bg-white/5 px-8 backdrop-blur-sm hover:bg-white/10"
              size="lg"
              variant="outline"
            >
              <span className="text-md">开始使用</span>
              <ChevronRightIcon className="size-4" />
            </Button>
          </Link>
        </motion.div>
      </div>
    </div>
  );
}
