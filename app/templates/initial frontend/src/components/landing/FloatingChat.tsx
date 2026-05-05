import { MessageCircle } from "lucide-react";
import { motion } from "framer-motion";

const FloatingChat = () => (
  <motion.button
    initial={{ scale: 0 }}
    animate={{ scale: 1 }}
    transition={{ delay: 1, type: "spring" }}
    className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full gradient-hero shadow-xl flex items-center justify-center hover:shadow-2xl transition-shadow"
    aria-label="Chat with us"
  >
    <MessageCircle className="h-6 w-6 text-primary-foreground" />
  </motion.button>
);

export default FloatingChat;
