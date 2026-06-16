import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact Us - MVPKIT AI",
  description: "Get in touch with our team. Let's discuss your startup platform vision.",
};

export default function ContactLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
