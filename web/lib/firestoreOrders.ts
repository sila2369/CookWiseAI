import {
  collection,
  doc,
  serverTimestamp,
  setDoc,
  type Timestamp,
} from "firebase/firestore";

import { getFirebaseDb } from "@/lib/firebase";

export type CheckoutOrderItem = {
  productId: string;
  name: string;
  quantity: number;
  unitPrice: number;
  lineTotal: number;
  imageUrl?: string | null;
};

export type CreateFirestoreOrderInput = {
  userId: string;
  items: CheckoutOrderItem[];
  totalAmount: number;
  address: string;
  paymentMethod: "CASH_ON_DELIVERY" | "CREDIT_CARD";
};

export type FirestoreOrderDocument = {
  orderId: string;
  userId: string;
  items: CheckoutOrderItem[];
  totalAmount: number;
  status: "beklemede" | "onaylandı";
  createdAt: Timestamp | ReturnType<typeof serverTimestamp>;
  address: string;
  paymentMethod: "CASH_ON_DELIVERY" | "CREDIT_CARD";
};

export async function createFirestoreOrder(input: CreateFirestoreOrderInput): Promise<string> {
  const db = getFirebaseDb();
  if (!db) {
    throw new Error("Firebase veritabanı başlatılamadı.");
  }

  const orderRef = doc(collection(db, "orders"));
  const orderId = orderRef.id;

  const safeTotal = Number(input.totalAmount.toFixed(2));
  const orderData: FirestoreOrderDocument = {
    orderId,
    userId: input.userId,
    items: input.items,
    totalAmount: safeTotal,
    status: "beklemede",
    createdAt: serverTimestamp(),
    address: input.address,
    paymentMethod: input.paymentMethod,
  };

  await setDoc(orderRef, orderData);
  return orderId;
}

