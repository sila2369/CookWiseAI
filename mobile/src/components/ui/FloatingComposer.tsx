import { Animated, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { palette, shadows } from "../../theme/palette";

type FloatingComposerProps = {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled?: boolean;
  scale: Animated.Value;
  onPressIn: () => void;
  onPressOut: () => void;
};

export default function FloatingComposer({
  value,
  onChange,
  onSend,
  disabled,
  scale,
  onPressIn,
  onPressOut,
}: FloatingComposerProps) {
  return (
    <View style={styles.wrap}>
      <Pressable style={styles.iconBtn}>
        <Text style={styles.iconText}>📎</Text>
      </Pressable>
      <TextInput
        style={styles.input}
        placeholder="CookWise AI ile konuş..."
        placeholderTextColor="#98A2B3"
        value={value}
        onChangeText={onChange}
        multiline
      />
      <Pressable style={styles.iconBtn}>
        <Text style={styles.iconText}>🎤</Text>
      </Pressable>
      <Animated.View style={{ transform: [{ scale }] }}>
        <Pressable
          onPress={onSend}
          disabled={disabled}
          onPressIn={onPressIn}
          onPressOut={onPressOut}
          style={[styles.sendBtn, disabled && { opacity: 0.5 }]}
        >
          <Text style={styles.sendText}>Gönder</Text>
        </Pressable>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "flex-end",
    borderRadius: 24,
    backgroundColor: "#FFFFFFF2",
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.14)",
    paddingVertical: 8,
    paddingHorizontal: 8,
    gap: 6,
    ...shadows.card,
  },
  iconBtn: {
    width: 36,
    height: 36,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#F2FBF6",
  },
  iconText: {
    fontSize: 16,
  },
  input: {
    flex: 1,
    minHeight: 36,
    maxHeight: 96,
    paddingHorizontal: 8,
    paddingTop: 8,
    color: palette.textPrimary,
    fontSize: 14,
    lineHeight: 20,
  },
  sendBtn: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 14,
    backgroundColor: palette.mint,
  },
  sendText: {
    color: "#fff",
    fontWeight: "700",
    fontSize: 12,
  },
});
