import type { ReactNode } from "react";
import { LinearGradient } from "expo-linear-gradient";
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

/** Web login/register ile aynı görsel token'lar */
const BG = "#F4FFF8";
const TEXT = "#1F2937";
const SLATE = "#475467";
const SLATE_LIGHT = "#64748B";
const EMERALD_BORDER = "rgba(167, 243, 208, 0.85)";
const EMERALD_SOFT = "rgba(236, 253, 245, 0.95)";
const LINK = "#0ea5b7";
const MINT = "#16C47F";
const CYAN = "#22D3EE";

export type AuthMode = "login" | "register" | "verify";

type AuthScreenProps = {
  authMode: AuthMode;
  setAuthMode: (mode: AuthMode) => void;
  fullName: string;
  setFullName: (v: string) => void;
  email: string;
  setEmail: (v: string) => void;
  password: string;
  setPassword: (v: string) => void;
  confirmPassword: string;
  setConfirmPassword: (v: string) => void;
  verificationCode: string;
  setVerificationCode: (v: string) => void;
  authLoading: boolean;
  authError: string;
  apiReachable: boolean | null;
  onLogin: () => void;
  onRegister: () => void;
  onVerify: () => void;
  onClearError: () => void;
};

function AuthField({
  label,
  icon,
  children,
}: {
  label: string;
  icon: string;
  children: ReactNode;
}) {
  return (
    <View style={styles.fieldBlock}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <View style={styles.inputShell}>
        <Text style={styles.inputIcon}>{icon}</Text>
        {children}
      </View>
    </View>
  );
}

export default function AuthScreen({
  authMode,
  setAuthMode,
  fullName,
  setFullName,
  email,
  setEmail,
  password,
  setPassword,
  confirmPassword,
  setConfirmPassword,
  verificationCode,
  setVerificationCode,
  authLoading,
  authError,
  apiReachable,
  onLogin,
  onRegister,
  onVerify,
  onClearError,
}: AuthScreenProps) {
  const isSocialInfo = authError.includes("şu anda aktif değil");
  const isGoogleReady = false;

  const title =
    authMode === "login"
      ? "CookWise’a hoş geldin"
      : authMode === "register"
        ? "CookWise hesabını oluştur"
        : "E-postanı doğrula";

  const subtitle =
    authMode === "login"
      ? "Tarif, akıllı sepet ve yapay zeka mutfak asistanına tek ekrandan ulaş."
      : authMode === "register"
        ? "Akıllı tarif, sepet önerisi ve AI mutfak asistanını hemen kullanmaya başla."
        : "Hesabını aktifleştirmek için e-postana gelen 6 haneli kodu gir.";

  const primaryLabel =
    authMode === "login"
      ? authLoading
        ? "Giriş yapılıyor..."
        : "Giriş Yap"
      : authMode === "register"
        ? authLoading
          ? "Hesap oluşturuluyor..."
          : "Hesap Oluştur"
        : authLoading
          ? "Doğrulanıyor..."
          : "Doğrula ve Giriş Yap";

  function onPrimaryPress() {
    if (authMode === "login") void onLogin();
    else if (authMode === "register") void onRegister();
    else void onVerify();
  }

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === "ios" ? "padding" : "height"}
    >
      <View style={styles.bg}>
        <View style={[styles.blob, styles.blobGreen]} />
        <View style={[styles.blob, styles.blobCyan]} />
        <View style={[styles.blob, styles.blobAmber]} />
        {Array.from({ length: 8 }).map((_, idx) => (
          <View
            key={`p-${idx}`}
            style={[
              styles.particle,
              { left: `${6 + idx * 11}%`, top: `${14 + (idx % 3) * 18}%` },
            ]}
          />
        ))}
      </View>

      <SafeAreaView style={styles.safe}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <View style={styles.logoRow}>
                <LinearGradient
                  colors={[MINT, CYAN]}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                  style={styles.logoIcon}
                >
                  <Text style={styles.logoMark}>CW</Text>
                </LinearGradient>
                <Text style={styles.logoText}>CookWise</Text>
              </View>
              <View style={styles.badge}>
                <Text style={styles.badgeText}>AI Kitchen Assistant</Text>
              </View>
            </View>

            <Text style={styles.title}>{title}</Text>
            <Text style={styles.subtitle}>{subtitle}</Text>

            {authMode === "login" ? (
              <View style={styles.formGap}>
                <AuthField label="E-POSTA" icon="✉️">
                  <TextInput
                    style={styles.input}
                    placeholder="ornek@email.com"
                    placeholderTextColor="#94a3b8"
                    keyboardType="email-address"
                    autoCapitalize="none"
                    value={email}
                    onChangeText={setEmail}
                  />
                </AuthField>
                <View style={styles.fieldBlock}>
                  <View style={styles.passwordLabelRow}>
                    <Text style={styles.fieldLabel}>ŞİFRE</Text>
                    <Pressable onPress={() => Alert.alert("CookWise", "Şifre sıfırlama yakında eklenecek.")}>
                      <Text style={styles.forgotLink}>Şifremi Unuttum</Text>
                    </Pressable>
                  </View>
                  <View style={styles.inputShell}>
                    <Text style={styles.inputIcon}>🔒</Text>
                    <TextInput
                      style={styles.input}
                      placeholder="••••••••"
                      placeholderTextColor="#94a3b8"
                      secureTextEntry
                      value={password}
                      onChangeText={setPassword}
                    />
                  </View>
                </View>
              </View>
            ) : null}

            {authMode === "register" ? (
              <View style={styles.formGap}>
                <AuthField label="AD SOYAD" icon="👤">
                  <TextInput
                    style={styles.input}
                    placeholder="Ahmet Yılmaz"
                    placeholderTextColor="#94a3b8"
                    value={fullName}
                    onChangeText={setFullName}
                  />
                </AuthField>
                <AuthField label="E-POSTA" icon="✉️">
                  <TextInput
                    style={styles.input}
                    placeholder="ornek@email.com"
                    placeholderTextColor="#94a3b8"
                    keyboardType="email-address"
                    autoCapitalize="none"
                    value={email}
                    onChangeText={setEmail}
                  />
                </AuthField>
                <AuthField label="ŞİFRE" icon="🔒">
                  <TextInput
                    style={styles.input}
                    placeholder="••••••••"
                    placeholderTextColor="#94a3b8"
                    secureTextEntry
                    value={password}
                    onChangeText={setPassword}
                  />
                </AuthField>
                <AuthField label="ŞİFRE TEKRAR" icon="🔒">
                  <TextInput
                    style={styles.input}
                    placeholder="••••••••"
                    placeholderTextColor="#94a3b8"
                    secureTextEntry
                    value={confirmPassword}
                    onChangeText={setConfirmPassword}
                  />
                </AuthField>
              </View>
            ) : null}

            {authMode === "verify" ? (
              <View style={styles.formGap}>
                <View style={styles.fieldBlock}>
                  <Text style={styles.fieldLabel}>DOĞRULAMA KODU</Text>
                  <TextInput
                    style={styles.codeInput}
                    placeholder="123456"
                    placeholderTextColor="#94a3b8"
                    keyboardType="number-pad"
                    maxLength={6}
                    value={verificationCode}
                    onChangeText={setVerificationCode}
                  />
                </View>
                <Pressable
                  onPress={() => {
                    setAuthMode("login");
                    setVerificationCode("");
                  }}
                >
                  <Text style={styles.inlineLink}>Giriş ekranına dön</Text>
                </Pressable>
              </View>
            ) : null}

            {!!authError ? (
              <View
                style={[
                  styles.errorBox,
                  isSocialInfo ? styles.errorBoxInfo : styles.errorBoxDanger,
                ]}
              >
                <Text style={isSocialInfo ? styles.errorTextInfo : styles.errorTextDanger}>{authError}</Text>
              </View>
            ) : null}

            <Pressable
              style={({ pressed }) => [styles.primaryWrap, pressed && { opacity: 0.92 }]}
              onPress={onPrimaryPress}
              disabled={authLoading}
            >
              <LinearGradient
                colors={[MINT, CYAN, MINT]}
                start={{ x: 0, y: 0.5 }}
                end={{ x: 1, y: 0.5 }}
                style={[styles.primaryBtn, authLoading && { opacity: 0.7 }]}
              >
                <Text style={styles.primaryBtnText}>{primaryLabel}</Text>
              </LinearGradient>
            </Pressable>

            {authMode === "login" ? (
              <>
                <View style={styles.dividerRow}>
                  <View style={styles.dividerLine} />
                  <Text style={styles.dividerText}>veya</Text>
                  <View style={styles.dividerLine} />
                </View>
                <View style={styles.socialRow}>
                  <Pressable
                    style={[styles.socialBtn, !isGoogleReady && { opacity: 0.55 }]}
                    disabled={!isGoogleReady}
                    onPress={() =>
                      Alert.alert(
                        "CookWise",
                        "Google ile giriş şu anda aktif değil. Lütfen e-posta ve şifre ile devam edin."
                      )
                    }
                  >
                    <Text style={styles.socialG}>G</Text>
                    <Text style={styles.socialLabel}>Google ile giriş</Text>
                  </Pressable>
                  <Pressable
                    style={styles.socialBtn}
                    onPress={() =>
                      Alert.alert(
                        "CookWise",
                        "Apple ile giriş şu anda aktif değil. Şimdilik e-posta ve şifre ile giriş yapabilirsiniz."
                      )
                    }
                  >
                    <Text style={styles.socialApple}></Text>
                    <Text style={styles.socialLabel}>Apple ile giriş</Text>
                  </Pressable>
                </View>
              </>
            ) : null}

            {authMode === "register" ? (
              <>
                <View style={styles.dividerRow}>
                  <View style={styles.dividerLine} />
                  <Text style={styles.dividerText}>veya</Text>
                  <View style={styles.dividerLine} />
                </View>
                <View style={styles.socialRow}>
                  <Pressable
                    style={[styles.socialBtn, !isGoogleReady && { opacity: 0.55 }]}
                    disabled={!isGoogleReady}
                    onPress={() =>
                      Alert.alert(
                        "CookWise",
                        "Google ile kayıt şu anda aktif değil. Lütfen e-posta ve şifre ile devam edin."
                      )
                    }
                  >
                    <Text style={styles.socialG}>G</Text>
                    <Text style={styles.socialLabel}>Google ile kayıt</Text>
                  </Pressable>
                  <Pressable
                    style={styles.socialBtn}
                    onPress={() =>
                      Alert.alert(
                        "CookWise",
                        "Apple ile kayıt şu anda aktif değil. Şimdilik e-posta ve şifre ile kayıt olabilirsiniz."
                      )
                    }
                  >
                    <Text style={styles.socialApple}></Text>
                    <Text style={styles.socialLabel}>Apple ile kayıt</Text>
                  </Pressable>
                </View>
              </>
            ) : null}

            <Text style={styles.footerText}>
              {authMode === "login" ? "Hesabın yok mu? " : authMode === "register" ? "Zaten hesabın var mı? " : ""}
              {authMode !== "verify" ? (
                <Text
                  style={styles.footerLink}
                  onPress={() => {
                    onClearError();
                    setAuthMode(authMode === "login" ? "register" : "login");
                    setVerificationCode("");
                  }}
                >
                  {authMode === "login" ? "Hemen Kayıt Ol" : "Giriş Yap"}
                </Text>
              ) : null}
            </Text>

            <Text style={styles.adminHint}>
              Yönetici misin?{" "}
              <Text style={styles.footerLink}>Admin girişi (web)</Text>
            </Text>

            <Text style={styles.apiHint}>
              Bağlantı: {apiReachable === null ? "…" : apiReachable ? "Çevrimiçi" : "Ulaşılamıyor"}
            </Text>
          </View>

          <View style={styles.heroCard}>
            <View style={styles.heroBadge}>
              <Text style={styles.heroBadgeText}>AI destekli mutfak deneyimi</Text>
            </View>
            <Text style={styles.heroTitle}>
              {authMode === "register"
                ? "Akıllı tarif ve sepet önerileriyle hızlı başlangıç"
                : "Tarif, alışveriş ve akıllı öneriler tek panelde"}
            </Text>
            <Text style={styles.heroSubtitle}>
              CookWise AI, ne pişireceğini planlar, stokta olan ürünlerle sepet önerir ve mutfak sürecini adım adım yönetir.
            </Text>
            <View style={styles.heroGrid}>
              <View style={styles.heroMini}>
                <LinearGradient colors={[MINT, CYAN]} style={styles.heroMiniIcon}>
                  <Text style={styles.heroMiniEmoji}>🤖</Text>
                </LinearGradient>
                <Text style={styles.heroMiniTitle}>AI Tarif Akışı</Text>
                <View style={styles.heroBubble}>
                  <Text style={styles.heroBubbleText}>“2 kişilik sebzeli makarna öner”</Text>
                </View>
                <View style={[styles.heroBubble, styles.heroBubbleOutline]}>
                  <Text style={styles.heroBubbleText}>Hazırlık 10 dk • Pişirme 18 dk</Text>
                </View>
              </View>
              <View style={styles.heroMini}>
                <LinearGradient colors={[CYAN, MINT]} style={styles.heroMiniIcon}>
                  <Text style={styles.heroMiniEmoji}>🛒</Text>
                </LinearGradient>
                <Text style={styles.heroMiniTitle}>Akıllı Sepet</Text>
                <Text style={styles.heroList}>- Domates Kg{"\n"}- Soğan Demet{"\n"}- Makarna 500g</Text>
              </View>
            </View>
            <View style={styles.heroRow2}>
              <View style={styles.heroWide}>
                <Text style={styles.heroWideTag}>✨ Öneri Kartı</Text>
                <Text style={styles.heroWideText}>Bugün için öneri: Mercimek çorbası + fırın sebze + ayran.</Text>
              </View>
              <View style={styles.heroWide}>
                <Text style={[styles.heroWideTag, { color: "#d97706" }]}>⭐ AI Notu</Text>
                <Text style={styles.heroWideText}>Haftalık plan oluşturarak alışveriş maliyetini düşürebilirsin.</Text>
              </View>
            </View>
          </View>
        </ScrollView>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: BG },
  bg: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: BG,
  },
  blob: {
    position: "absolute",
    borderRadius: 999,
    opacity: 0.35,
  },
  blobGreen: {
    width: 360,
    height: 360,
    left: -100,
    top: -80,
    backgroundColor: "rgba(22, 196, 127, 0.22)",
  },
  blobCyan: {
    width: 340,
    height: 340,
    right: -60,
    top: 40,
    backgroundColor: "rgba(34, 211, 238, 0.2)",
  },
  blobAmber: {
    width: 280,
    height: 280,
    left: "25%",
    bottom: -40,
    backgroundColor: "rgba(245, 158, 11, 0.16)",
  },
  particle: {
    position: "absolute",
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "rgba(22, 196, 127, 0.35)",
  },
  safe: { flex: 1 },
  scroll: {
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 32,
    gap: 16,
  },
  card: {
    maxWidth: 460,
    width: "100%",
    alignSelf: "center",
    borderRadius: 30,
    borderWidth: 1,
    borderColor: EMERALD_BORDER,
    backgroundColor: "rgba(255,255,255,0.78)",
    paddingHorizontal: 20,
    paddingVertical: 24,
    shadowColor: "#22d3ee",
    shadowOffset: { width: 0, height: 28 },
    shadowOpacity: 0.18,
    shadowRadius: 40,
    elevation: 8,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 22,
  },
  logoRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  logoIcon: {
    width: 36,
    height: 36,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  logoMark: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "900",
    letterSpacing: 0.2,
  },
  logoText: {
    fontSize: 23,
    fontWeight: "700",
    color: TEXT,
    letterSpacing: -0.5,
  },
  badge: {
    borderRadius: 999,
    borderWidth: 1,
    borderColor: EMERALD_BORDER,
    backgroundColor: EMERALD_SOFT,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  badgeText: { fontSize: 11, color: "#047857", fontWeight: "600" },
  title: {
    fontSize: 28,
    fontWeight: "700",
    color: TEXT,
    lineHeight: 33,
  },
  subtitle: {
    marginTop: 8,
    fontSize: 14,
    lineHeight: 21,
    color: SLATE_LIGHT,
  },
  formGap: { marginTop: 18, gap: 14 },
  fieldBlock: { gap: 8 },
  fieldLabel: {
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 2,
    color: SLATE,
    textTransform: "uppercase",
  },
  passwordLabelRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  forgotLink: { fontSize: 12, color: LINK, fontWeight: "600" },
  inputShell: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: EMERALD_BORDER,
    backgroundColor: "rgba(255,255,255,0.88)",
    paddingLeft: 10,
  },
  inputIcon: { fontSize: 15, marginRight: 4, opacity: 0.85 },
  input: {
    flex: 1,
    paddingVertical: 12,
    paddingRight: 14,
    fontSize: 14,
    color: TEXT,
  },
  codeInput: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: EMERALD_BORDER,
    backgroundColor: "rgba(255,255,255,0.88)",
    paddingVertical: 12,
    fontSize: 20,
    letterSpacing: 8,
    textAlign: "center",
    color: TEXT,
  },
  inlineLink: {
    marginTop: 4,
    fontSize: 13,
    color: LINK,
    fontWeight: "600",
  },
  errorBox: {
    marginTop: 14,
    borderRadius: 16,
    borderWidth: 1,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  errorBoxDanger: {
    borderColor: "rgba(251, 113, 133, 0.55)",
    backgroundColor: "rgba(255, 241, 242, 0.95)",
  },
  errorBoxInfo: {
    borderColor: "rgba(167, 243, 208, 0.45)",
    backgroundColor: EMERALD_SOFT,
  },
  errorTextDanger: { fontSize: 14, color: "#be123c" },
  errorTextInfo: { fontSize: 14, color: "#065f46" },
  primaryWrap: { marginTop: 18, borderRadius: 16, overflow: "hidden" },
  primaryBtn: {
    paddingVertical: 14,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: CYAN,
    shadowOffset: { width: 0, height: 14 },
    shadowOpacity: 0.35,
    shadowRadius: 20,
    elevation: 4,
  },
  primaryBtnText: { color: "#fff", fontSize: 14, fontWeight: "600" },
  dividerRow: {
    marginTop: 22,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  dividerLine: { flex: 1, height: 1, backgroundColor: "rgba(167, 243, 208, 0.85)" },
  dividerText: { fontSize: 12, color: SLATE_LIGHT },
  socialRow: { marginTop: 10, flexDirection: "row", gap: 8 },
  socialBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: EMERALD_BORDER,
    backgroundColor: "rgba(255,255,255,0.88)",
    paddingVertical: 11,
    paddingHorizontal: 8,
  },
  socialG: { fontSize: 14, fontWeight: "800", color: CYAN },
  socialApple: { fontSize: 16, color: TEXT },
  socialLabel: { fontSize: 12, fontWeight: "600", color: "#334155" },
  footerText: {
    marginTop: 22,
    textAlign: "center",
    fontSize: 14,
    color: SLATE_LIGHT,
  },
  footerLink: { fontWeight: "700", color: LINK },
  adminHint: {
    marginTop: 8,
    textAlign: "center",
    fontSize: 12,
    color: SLATE_LIGHT,
  },
  apiHint: {
    marginTop: 10,
    textAlign: "center",
    fontSize: 11,
    color: "#94a3b8",
  },
  heroCard: {
    maxWidth: 460,
    width: "100%",
    alignSelf: "center",
    borderRadius: 34,
    borderWidth: 1,
    borderColor: EMERALD_BORDER,
    backgroundColor: "rgba(255,255,255,0.72)",
    padding: 20,
    marginTop: 4,
    shadowColor: MINT,
    shadowOffset: { width: 0, height: 32 },
    shadowOpacity: 0.12,
    shadowRadius: 36,
    elevation: 6,
  },
  heroBadge: {
    alignSelf: "flex-end",
    borderRadius: 999,
    borderWidth: 1,
    borderColor: EMERALD_BORDER,
    backgroundColor: EMERALD_SOFT,
    paddingHorizontal: 10,
    paddingVertical: 5,
    marginBottom: 12,
  },
  heroBadgeText: { fontSize: 11, color: "#047857", fontWeight: "600" },
  heroTitle: {
    fontSize: 22,
    fontWeight: "600",
    color: TEXT,
    lineHeight: 28,
  },
  heroSubtitle: {
    marginTop: 10,
    fontSize: 13,
    lineHeight: 20,
    color: SLATE_LIGHT,
  },
  heroGrid: { marginTop: 16, flexDirection: "row", gap: 10 },
  heroMini: {
    flex: 1,
    borderRadius: 22,
    borderWidth: 1,
    borderColor: EMERALD_BORDER,
    backgroundColor: "rgba(255,255,255,0.9)",
    padding: 12,
  },
  heroMiniIcon: {
    width: 36,
    height: 36,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  heroMiniEmoji: { fontSize: 16 },
  heroMiniTitle: { fontSize: 13, fontWeight: "700", color: TEXT },
  heroBubble: {
    marginTop: 8,
    borderRadius: 12,
    backgroundColor: EMERALD_SOFT,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  heroBubbleOutline: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "rgba(34, 211, 238, 0.35)",
  },
  heroBubbleText: { fontSize: 11, color: SLATE_LIGHT, lineHeight: 16 },
  heroList: { marginTop: 8, fontSize: 11, color: SLATE_LIGHT, lineHeight: 18 },
  heroRow2: { marginTop: 12, gap: 10 },
  heroWide: {
    borderRadius: 22,
    borderWidth: 1,
    borderColor: EMERALD_BORDER,
    backgroundColor: "rgba(255,255,255,0.9)",
    padding: 12,
  },
  heroWideTag: {
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.2,
    color: CYAN,
    marginBottom: 6,
    textTransform: "uppercase",
  },
  heroWideText: { fontSize: 13, color: "#334155", lineHeight: 19 },
});
