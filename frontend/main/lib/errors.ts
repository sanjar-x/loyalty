export class AppError extends Error {
  constructor(message: string, public code?: string) {
    super(message);
    this.name = "AppError";
  }
}

export class ApiError extends AppError {
  constructor(
    message: string,
    public status: number,
    public detail?: string,
  ) {
    super(message, `API_${status}`);
    this.name = "ApiError";
  }
}

export class NetworkError extends AppError {
  constructor(message: string = "Network error") {
    super(message, "NETWORK_ERROR");
    this.name = "NetworkError";
  }
}
