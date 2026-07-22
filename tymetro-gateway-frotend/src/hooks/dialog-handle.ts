import { reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { getDocument } from "../utils/service";

export function DialogHandle() {
  const route = useRoute();

  const parts = reactive({} as any);
  const dialog = reactive({
    title: "使用者資料",
    name: "",
    code: "",
    visible: false,
  });

  const table = reactive({
    options: {} as any,
    records: [] as any[],
    columns: [] as any[],
    actions: [] as any[],
  });

  const loadDialog = async (document: string | undefined = undefined) => {
    return new Promise((resolve, reject) => {
      let component = route.name?.toString();

      if (document != undefined) {
        component = document;
      }
      getDocument(component)
        .then((response: any) => {
          const content = JSON.parse(response.data.content);
          const dialog = content.find((x: any) => x.sectionType == "Dialog");
          resolve(true);
        })
        .catch((e) => {
          reject(false);
        });
    });
    // 處理 Dialog 資料
  };
  return {
    loadDialog,
  };
}
