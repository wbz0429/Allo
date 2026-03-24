export type Session = {
  session: {
    token: string;
    userId: string;
    expiresAt: string;
  };
  user: {
    id: string;
    email: string;
    name: string;
  };
};

export type AuthClientResult = {
  data: Session | null;
  error: { message: string } | null;
};
