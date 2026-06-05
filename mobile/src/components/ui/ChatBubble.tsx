import { StyleSheet, Text, View } from "react-native";
import type { ChatMessage } from "../../types/app";
import { palette, shadows } from "../../theme/palette";

type ChatBubbleProps = {
  message: ChatMessage;
};

export default function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.role === "user";
  return (
    <View style={[styles.bubble, isUser ? styles.userBubble : styles.assistantBubble]}>
      <Text style={[styles.text, isUser && styles.userText]}>{message.content}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  bubble: {
    maxWidth: "90%",
    borderRadius: 18,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: palette.mint,
    ...shadows.soft,
  },
  assistantBubble: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(255,255,255,0.95)",
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.12)",
  },
  text: {
    color: palette.textPrimary,
    fontSize: 13.5,
    lineHeight: 21,
  },
  userText: {
    color: "#FFFFFF",
  },
});
