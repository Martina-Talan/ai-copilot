export async function encoding_for_model() {
    return {
      encode: (text: string) => Array(text.length).fill(0),
    };
  }
  