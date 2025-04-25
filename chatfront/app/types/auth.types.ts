export interface CustomUser {
  id: string;
  username: string;
  group_name: string;
  access_token: string;
  token_type: string;
  is_admin?: boolean;
  user?: {
    id: string;
    username: string;
    group_name: string;
    is_admin?: boolean;
  };
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthResponse {
  id: string;
  username: string;
  group_name: string;
  access_token: string;
  token_type: string;
}
