export interface ReferralLink {
  link: string;
  code?: string;
}

export interface ReferralStats {
  clicked: number;
  installed: number;
  promo_issued_total: number;
}

export interface ActiveDiscount {
  code: string;
  percent: number;
  expires_at: string | null;
  max_amount: number;
}

export interface InvitedUser {
  invite_id: string;
  invitee_id: number;
  invitee_tg_id: string;
  invitee_username: string | null;
  status: string;
  created_at: string;
}

export interface InvitedUsersResponse {
  items: InvitedUser[];
}
