(() => {
  "use strict";
  const U = window.DrawpicUI,
    { state, $, e, icon, call, buttonAction, toast } = U;
  const sections = { general: "通用配置", persona: "人物参考图", review: "审核配置", access: "黑白名单", style: "风格预设" };
  const sourceSection = (name) => ["persona", "review", "access"].includes(name) ? "general" : name;
  const personaField = (key) => /^persona_reference_/.test(key);
  const reviewField = (key) => /^(prompt|image)_review_/.test(key);
  const accessField = (key) => /^(group|private)_access_/.test(key);
  const belongsToSection = (name, key) => name === "style" ||
    (name === "persona" ? personaField(key) : name === "review" ? reviewField(key) : name === "access" ? accessField(key) : !reviewField(key) && !accessField(key) && !personaField(key));
  U.views.settings = async () => {
    let selected = Object.hasOwn(sections, state.settingsSection)
      ? state.settingsSection
      : "general";
    const revision = state.data.revision;
    const readers = {};
    const save = $("#save-settings");
    $("#workspace-content").innerHTML =
      `<div class="settings-layout"><div class="settings-tabs" role="tablist" aria-label="配置分类">${Object.entries(
        sections,
      )
        .map(
          ([name, title]) =>
            `<button id="settings-tab-${name}" class="settings-tab" data-section="${name}" role="tab" aria-controls="settings-panel-${name}">${title}</button>`,
        )
        .join(
          "",
        )}</div><section class="panel"><div class="panel-header"><div><h2 id="settings-heading"></h2><p class="hint" id="settings-description"></p></div><button type="button" id="reset-settings" class="button secondary compact">恢复当前分类默认</button></div><form id="settings-form"></form></section></div>`;
    const form = $("#settings-form");
    let requiresRefresh = false;
    let referenceBusy = false;
    function renderReferences(panel) {
      const gallery = document.createElement("div");
      gallery.className = "field full persona-gallery";
      gallery.innerHTML = `<label>人物参考图</label><div class="source-list" data-persona-images></div><div><button type="button" class="button secondary compact" data-persona-upload>${icon("upload")}添加参考图</button><input type="file" accept="image/png,image/jpeg,image/webp" multiple hidden data-persona-file></div><p class="hint">最多 3 张，每张不超过 6 MiB。图片上传或移除后立即保存；开关和姓名点击“保存全部设置”生效。</p>`;
      panel.append(gallery);
      const upload = $("[data-persona-upload]", gallery);
      const input = $("[data-persona-file]", gallery);
      input.addEventListener("input", (event) => event.stopPropagation());
      const images = $("[data-persona-images]", gallery);
      const current = () => state.data.persona_references || { revision: 0, images: [] };
      function paint() {
        images.innerHTML = current().images.map((item, index) =>
          `<div class="source-item"><img src="${e(item.preview)}" alt="人物参考图 ${index + 1}"><button type="button" class="icon-button" data-reference-id="${e(item.id)}" aria-label="移除人物参考图 ${index + 1}">${icon("close")}</button></div>`).join("");
        upload.disabled = referenceBusy || current().images.length >= 3;
        for (const button of images.querySelectorAll("[data-reference-id]")) {
          button.disabled = referenceBusy;
          button.onclick = () => change(async () => {
            state.data.persona_references = await call("action", "persona_remove", {
              reference_id: button.dataset.referenceId, revision: current().revision,
            });
            toast("参考图已移除");
          });
        }
      }
      async function change(operation) {
        if (referenceBusy) return;
        referenceBusy = true;
        save.disabled = true;
        $("#reset-settings").disabled = true;
        paint();
        try { await operation(); }
        catch (error) { U.error(error); }
        finally {
          referenceBusy = false;
          if (panel.isConnected) {
            save.disabled = requiresRefresh;
            $("#reset-settings").disabled = requiresRefresh;
            upload.innerHTML = `${icon("upload")}添加参考图`;
            paint();
          }
        }
      }
      upload.onclick = () => input.click();
      input.onchange = () => {
        const files = [...input.files];
        input.value = "";
        if (!files.length) return;
        if (files.length + current().images.length > 3) return toast("最多保存 3 张人物参考图");
        if (files.some((file) => file.size > 6 * 1024 * 1024)) return toast("每张人物参考图不能超过 6 MiB");
        change(async () => {
          for (const file of files) {
            const source = await call("upload", "source", {}, file, {
              onProgress: (percent) => { upload.textContent = `上传中 ${Math.round(percent)}%`; },
            });
            state.data.persona_references = await call("action", "persona_add", {
              source_id: source.source_id, revision: current().revision,
            });
          }
          toast("参考图已保存");
        });
      };
      paint();
    }
    function renderSection(name, values) {
      const panel = document.createElement("section");
      panel.id = `settings-panel-${name}`;
      panel.dataset.settingsPanel = name;
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", `settings-tab-${name}`);
      panel.hidden = name !== selected;
      const fields = Object.fromEntries(
        Object.entries(state.data.schema.sections[sourceSection(name)].fields)
          .filter(([key]) => belongsToSection(name, key)),
      );
      panel.innerHTML = U.forms.html(fields, values);
      const old = $(`#${panel.id}`, form);
      if (old) old.replaceWith(panel);
      else form.append(panel);
      const read = U.forms.bind(panel, fields, values);
      // 通用、审核和黑白名单共享持久化配置，只读取当前分类的字段，避免覆盖其他分类草稿。
      readers[name] = () => {
        const result = read();
        return Object.fromEntries(Object.keys(fields).map((key) => [key, result[key]]));
      };
      if (name === "persona") renderReferences(panel);
    }
    for (const name of Object.keys(sections))
      renderSection(name, structuredClone(state.data.settings[sourceSection(name)]));
    function activate(name, reveal = false) {
      selected = state.settingsSection = name;
      $("#settings-heading").textContent = sections[name];
      $("#settings-description").textContent =
        name === "style"
          ? "把常用风格保存为提示词模板，各分类的修改可一起保存。"
          : name === "review"
            ? "分别设置提示词审核和生成图片审核，使用 MaiBot 配置的审核模型。切换分类保留草稿。"
          : name === "access"
            ? "分别设置群聊和私聊的访问规则。填写群号、QQ 号或 QQ 官方 OpenID，无需会话哈希；保存后对新的命令、AI 工具和指定会话的任务生效。"
          : name === "persona"
            ? "本人出镜自动使用参考图。请选择支持图生图及对应源图数量的模型；风景、物品和其他人物照照常处理。"
          : "切换分类会保留草稿，点击右下角“保存全部设置”统一保存。";
      for (const tab of document.querySelectorAll("[data-section]")) {
        const active = tab.dataset.section === name;
        tab.classList.toggle("active", active);
        tab.setAttribute("aria-selected", String(active));
        tab.tabIndex = active ? 0 : -1;
      }
      for (const panel of form.children)
        panel.hidden = panel.dataset.settingsPanel !== name;
      if (reveal) $("#settings-heading").scrollIntoView({ block: "start", behavior: "instant" });
    }
    const tabs = [...document.querySelectorAll("[data-section]")];
    for (const [index, tab] of tabs.entries()) {
      tab.onclick = () => activate(tab.dataset.section, true);
      tab.onkeydown = (event) => {
        let target;
        if (["ArrowRight", "ArrowDown"].includes(event.key))
          target = (index + 1) % tabs.length;
        else if (["ArrowLeft", "ArrowUp"].includes(event.key))
          target = (index + tabs.length - 1) % tabs.length;
        else if (event.key === "Home") target = 0;
        else if (event.key === "End") target = tabs.length - 1;
        else return;
        event.preventDefault();
        tabs[target].focus();
        activate(tabs[target].dataset.section, true);
      };
    }
    const updateNotice = () => {
      $("#settings-unsaved").hidden = !state.dirty;
    };
    form.addEventListener("input", updateNotice);
    form.addEventListener("click", updateNotice);
    $("#reset-settings").onclick = () => {
      renderSection(selected, structuredClone(state.data.defaults[sourceSection(selected)]));
      state.dirty = true;
      updateNotice();
      toast("已恢复当前分类默认值，其他分类草稿保留，保存后生效");
    };
    const submitAll = () => {
      const invalid = form.querySelector(":invalid");
      if (invalid)
        activate(
          invalid.closest("[data-settings-panel]").dataset.settingsPanel,
        );
      U.submitForm(form);
    };
    save.onclick = submitAll;
    form.addEventListener("keydown", (event) => {
      if (
        event.key === "Enter" &&
        event.target.tagName === "INPUT" &&
        !event.isComposing
      ) {
        event.preventDefault();
        submitAll();
      }
    });
    form.onsubmit = (event) => {
      event.preventDefault();
      if (form.inert || requiresRefresh || referenceBusy) return;
      buttonAction(save, async () => {
        const all = {
          general: { ...state.data.settings.general, ...readers.general(), ...readers.persona(), ...readers.review(), ...readers.access() },
          style: readers.style(),
        };
        form.inert = true;
        $("#reset-settings").disabled = true;
        try {
          const result = await call("action", "settings_save", {
            config_json: JSON.stringify(all),
            revision,
          });
          if (form.isConnected) {
            state.dirty = false;
            updateNotice();
          }
          let refreshError = null;
          try {
            await U.bootstrap();
            if (form.isConnected && state.view === "settings") await U.render();
          } catch (error) {
            refreshError = error;
            requiresRefresh = true;
          }
          U.savedNotice(result, "全部设置已保存", refreshError);
        } finally {
          if (form.isConnected) {
            form.inert = requiresRefresh;
            $("#reset-settings").disabled = requiresRefresh;
          }
        }
      }).finally(() => {
        if (form.isConnected && requiresRefresh) save.disabled = true;
      });
    };
    activate(selected);
    updateNotice();
  };
})();
