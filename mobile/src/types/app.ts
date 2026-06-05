export type AuthUser = {
  id: string;
  full_name: string;
  email: string;
  is_admin: boolean;
};

export type LoginResponse = {
  access_token: string;
  user: AuthUser;
};

export type Category = {
  id: string;
  name: string;
  slug: string;
};

export type Product = {
  id: string;
  name: string;
  price: number;
  stock: number;
  category_id: string;
  unit?: string | null;
  image_url?: string | null;
  is_promoted?: boolean;
  promotion_type?: string | null;
  promotion_label?: string | null;
  discounted_price?: number | null;
  promotion_buy_quantity?: number | null;
  promotion_pay_quantity?: number | null;
};

export type CartItem = {
  product_id: string;
  name: string;
  price: number;
  original_price?: number | null;
  promotion_label?: string | null;
  quantity: number;
  subtotal: number;
};

export type CartResponse = {
  id: string;
  user_id: string;
  items: CartItem[];
  total_price: number;
};

export type OrderItem = {
  product_id: string;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
};

export type Order = {
  id: string;
  status: string;
  items: OrderItem[];
  total_price: number;
  delivery_address: string;
  payment_method: string;
  created_at: string;
};

export type OrdersResponse = {
  items: Order[];
  total: number;
};

export type FavoritesResponse = {
  items?: { id: string }[];
  total_count: number;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};
