declare module "type-fest" {
  export type SetOptional<BaseType, Keys extends keyof BaseType> = Omit<BaseType, Keys> &
    Partial<Pick<BaseType, Keys>>;

  export type SetRequired<BaseType, Keys extends keyof BaseType> = Omit<BaseType, Keys> &
    Required<Pick<BaseType, Keys>>;

  export type RequiredDeep<T> = T extends (...args: any[]) => unknown
    ? T
    : T extends readonly (infer U)[]
      ? ReadonlyArray<RequiredDeep<U>>
      : T extends object
        ? { [K in keyof T]-?: RequiredDeep<T[K]> }
        : T;
}
