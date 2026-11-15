/** Catch entry-module/configuration failures before they can leave an empty root. */
export async function startApplication<T>(load: () => Promise<T>, onLoaded: (module: T) => void, onFailed: (error: unknown) => void): Promise<void> {
  try {
    onLoaded(await load())
  } catch (error) {
    onFailed(error)
  }
}
