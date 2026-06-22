export type ResourceErrors<TName extends string> = Partial<Record<TName, string>>;

export const getResourceError = (_error: unknown, fallback: string) => fallback;

export const settledValue = <T>(
  result: PromiseSettledResult<T>,
  fallback: T
): T => (result.status === "fulfilled" ? result.value : fallback);

export const addSettledError = <TName extends string, TValue>(
  errors: ResourceErrors<TName>,
  name: TName,
  result: PromiseSettledResult<TValue>,
  fallback: string
) => {
  if (result.status === "rejected") {
    errors[name] = getResourceError(result.reason, fallback);
  }
};

export const hasResourceErrors = <TName extends string>(
  errors: ResourceErrors<TName>
) => Object.keys(errors).length > 0;
