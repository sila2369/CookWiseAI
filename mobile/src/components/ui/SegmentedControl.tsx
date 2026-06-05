import { LayoutAnimation, Platform, Pressable, StyleSheet, Text, UIManager, View } from "react-native";
import { palette, shadows } from "../../theme/palette";

if (Platform.OS === "android" && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

type Option = {
  value: string;
  label: string;
};

type SegmentedControlProps = {
  options: readonly Option[];
  value: string;
  onChange: (next: string) => void;
};

export default function SegmentedControl({ options, value, onChange }: SegmentedControlProps) {
  return (
    <View style={styles.wrap}>
      {options.map((option) => {
        const active = option.value === value;
        return (
          <Pressable
            key={option.value}
            onPress={() => {
              LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
              onChange(option.value);
            }}
            style={[styles.pill, active && styles.pillActive]}
          >
            <Text style={[styles.pillText, active && styles.pillTextActive]}>{option.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    backgroundColor: "#EEF6F1",
    borderRadius: 18,
    padding: 4,
    gap: 4,
  },
  pill: {
    flex: 1,
    borderRadius: 14,
    paddingVertical: 9,
    alignItems: "center",
    justifyContent: "center",
  },
  pillActive: {
    backgroundColor: palette.surface,
    borderWidth: 1,
    borderColor: "rgba(23,182,122,0.18)",
    ...shadows.soft,
  },
  pillText: {
    color: palette.textSecondary,
    fontSize: 12,
    fontWeight: "600",
  },
  pillTextActive: {
    color: palette.mintDark,
    fontWeight: "700",
  },
});
