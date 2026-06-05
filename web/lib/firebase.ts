import { initializeApp, getApps, getApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  setPersistence,
  browserLocalPersistence,
} from "firebase/auth";
import { getFirestore, type Firestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

let activeGooglePopupPromise: Promise<string> | null = null;
let firestoreDb: Firestore | null = null;

function ensureFirebaseConfig() {
  const missing = Object.entries(firebaseConfig)
    .filter(([, value]) => !value)
    .map(([key]) => key);

  if (missing.length > 0) {
    throw new Error("Google ile giriş şu anda aktif değil. Lütfen e-posta ve şifre ile devam edin.");
  }
}

function getFirebaseApp() {
  ensureFirebaseConfig();
  return getApps().length ? getApp() : initializeApp(firebaseConfig);
}

export function getFirebaseDb(): Firestore | null {
  try {
    const app = getFirebaseApp();
    if (!firestoreDb) {
      firestoreDb = getFirestore(app);
    }
    return firestoreDb;
  } catch {
    return null;
  }
}

export async function signInWithGoogleAndGetIdToken(): Promise<string> {
  if (activeGooglePopupPromise) {
    return activeGooglePopupPromise;
  }

  activeGooglePopupPromise = (async () => {
  const app = getFirebaseApp();
  const auth = getAuth(app);
  await setPersistence(auth, browserLocalPersistence);

  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });

    try {
      const result = await signInWithPopup(auth, provider);
      return await result.user.getIdToken(true);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "";
      if (message.includes("Pending promise was never set")) {
        throw new Error("Google giriş penceresi başlatılamadı. Lütfen tekrar deneyin.");
      }
      throw err;
    } finally {
      activeGooglePopupPromise = null;
    }
  })();

  return activeGooglePopupPromise;
}
