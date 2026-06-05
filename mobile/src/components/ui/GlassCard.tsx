import { PropsWithChildren } from "react";
import { StyleSheet, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { palette, shadows } from "../../theme/palette";

type GlassCardProps = PropsWithChildren<{
  padded?: boolean;
}>;

export default function GlassCard({ children, padded = true }: GlassCardProps) {
  return (
    <LinearGradient
      colors={["rgba(255,255,255,0.96)", "rgba(247,254,251,0.92)"]}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={styles.gradient}
    >
      <View style={[styles.inner, padded && styles.innerPadded]}>{children}</View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  gradient: {
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.10)",
    ...shadows.card,
  },
  inner: {
    borderRadius: 24,
    backgroundColor: "transparent",
  },
  innerPadded: {
    padding: 14,
  },
});
