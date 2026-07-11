const API_BASE = "http://localhost:8000/api";

const app = Vue.createApp({
  data() {
    return {
      view: "upload",
      loading: false,
      loadingMessage: "",
      sessions: [],
      currentSession: null,
      eda: null,
      edaTab: "overview",
      trainConfig: {
        targetCol: "",
        testSize: 0.2,
        algorithms: ["Random Forest", "Logistic Regression", "Gradient Boosting"],
        tuneHyperparams: false,
      },
      training: false,
      results: null,
      plots: null,
      selectedModel: null,
      toast: null,
      suggestedTargets: [],
      featureTypes: {},
    };
  },

  computed: {
    numericColumns() {
      if (!this.eda) return [];
      return this.eda.overview.columns.filter(
        (c) =>
          this.eda.overview.dtypes[c] &&
          (this.eda.overview.dtypes[c].includes("float") ||
            this.eda.overview.dtypes[c].includes("int"))
      );
    },
    missingCount() {
      if (!this.eda) return 0;
      return Object.values(this.eda.overview.missing).reduce((a, b) => a + b, 0);
    },
    numericCount() {
      return this.numericColumns.length;
    },
    categoricalCount() {
      if (!this.eda) return 0;
      return Object.values(this.eda.overview.dtypes).filter(
        (t) => t === "object"
      ).length;
    },
    detectedProblemType() {
      if (!this.trainConfig.targetCol || !this.eda) return null;
      const col = this.trainConfig.targetCol;
      const dtype = this.eda.overview.dtypes[col];
      const unique = this.eda.overview.unique_counts[col];
      if (dtype === "object" || unique <= 15) return "classification";
      return "regression";
    },
    availableAlgorithms() {
      if (this.detectedProblemType === "classification") {
        return [
          "Logistic Regression",
          "Random Forest",
          "Gradient Boosting",
          "SVM",
          "KNN",
          "Decision Tree",
        ];
      }
      return [
        "Linear Regression",
        "Ridge",
        "Lasso",
        "Random Forest",
        "Gradient Boosting",
        "SVR",
        "KNN",
      ];
    },
    selectedModelData() {
      if (!this.results || !this.selectedModel) return {};
      const m = this.results.models.find(
        (m) => m.algorithm === this.selectedModel
      );
      return m || {};
    },
    maxCM() {
      if (!this.selectedModelData.metrics?.confusion_matrix) return 1;
      return Math.max(
        ...this.selectedModelData.metrics.confusion_matrix.flat()
      );
    },
  },

  methods: {
    async fetchSessions() {
      try {
        const res = await fetch(`${API_BASE}/sessions`);
        const data = await res.json();
        this.sessions = data.sessions || [];
      } catch {
        this.showToast("Cannot connect to backend. Is the server running?", "error");
      }
    },

    handleDrop(e) {
      e.target.classList.remove("dragover");
      const file = e.dataTransfer.files[0];
      if (file) this.uploadFile(file);
    },

    handleUpload(e) {
      const file = e.target.files[0];
      if (file) this.uploadFile(file);
      e.target.value = "";
    },

    async uploadFile(file) {
      if (!file.name.endsWith(".csv")) {
        this.showToast("Only CSV files are supported", "error");
        return;
      }
      this.loading = true;
      this.loadingMessage = "Uploading & analyzing...";
      const formData = new FormData();
      formData.append("file", file);
      try {
        const res = await fetch(`${API_BASE}/upload`, {
          method: "POST",
          body: formData,
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Upload failed");
        }
        const data = await res.json();
        this.currentSession = {
          id: data.session_id,
          filename: file.name,
          rows: data.eda.overview.shape.rows,
          columns: data.eda.overview.shape.columns,
        };
        this.eda = data.eda;
        this.featureTypes = data.feature_types || {};
        this.suggestedTargets = data.suggested_targets || [];
        this.edaTab = "overview";
        this.results = null;
        this.plots = null;
        this.selectedModel = null;
        this.trainConfig.targetCol = "";
        this.trainConfig.algorithms = this.availableAlgorithms.slice(0, 3);
        this.showToast("Dataset uploaded & analyzed", "success");
        await this.fetchSessions();
      } catch (err) {
        this.showToast(err.message, "error");
      } finally {
        this.loading = false;
      }
    },

    async loadSession(sessionId) {
      this.loading = true;
      this.loadingMessage = "Loading session...";
      try {
        const res = await fetch(`${API_BASE}/eda/${sessionId}`);
        if (!res.ok) throw new Error("Session not found");
        const data = await res.json();
        const s = this.sessions.find((s) => s.id === sessionId);
        this.currentSession = { ...s, id: sessionId };
        this.eda = data.eda;
        this.edaTab = "overview";
        this.results = null;
        this.plots = null;
        this.selectedModel = null;
        this.trainConfig.targetCol = data.eda.target_col || "";
        this.trainConfig.algorithms = this.availableAlgorithms.slice(0, 3);

        if (s && s.trained) {
          try {
            const res2 = await fetch(`${API_BASE}/results/${sessionId}`);
            if (res2.ok) {
              const data2 = await res2.json();
              this.results = data2.results;
            }
          } catch {}
        }

        this.view = "upload";
        this.showToast("Session loaded", "success");
      } catch (err) {
        this.showToast(err.message, "error");
      } finally {
        this.loading = false;
      }
    },

    toggleAlgo(algo) {
      const idx = this.trainConfig.algorithms.indexOf(algo);
      if (idx >= 0) {
        if (this.trainConfig.algorithms.length > 1) {
          this.trainConfig.algorithms.splice(idx, 1);
        }
      } else {
        this.trainConfig.algorithms.push(algo);
      }
    },

    async startTraining() {
      if (!this.trainConfig.targetCol || this.trainConfig.algorithms.length === 0) {
        this.showToast("Select a target column and at least one algorithm", "error");
        return;
      }
      this.training = true;
      this.loading = true;
      this.loadingMessage = "Training models...";
      try {
        const formData = new FormData();
        formData.append("target_col", this.trainConfig.targetCol);
        formData.append("algorithms", this.trainConfig.algorithms.join(","));
        formData.append("test_size", String(this.trainConfig.testSize));
        formData.append("tune_hyperparams", String(this.trainConfig.tuneHyperparams));
        const res = await fetch(`${API_BASE}/train/${this.currentSession.id}`, {
          method: "POST",
          body: formData,
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Training failed");
        }
        const data = await res.json();
        this.results = data.results;
        this.plots = data.plots || {};
        this.selectedModel = data.results.best_model;
        this.showToast("Training complete!", "success");
        await this.fetchSessions();
      } catch (err) {
        this.showToast(err.message, "error");
      } finally {
        this.training = false;
        this.loading = false;
      }
    },

    async deleteSession() {
      if (!confirm("Delete this session and all results?")) return;
      try {
        await fetch(`${API_BASE}/sessions/${this.currentSession.id}`, {
          method: "DELETE",
        });
        this.currentSession = null;
        this.eda = null;
        this.results = null;
        this.plots = null;
        this.showToast("Session deleted", "success");
        await this.fetchSessions();
      } catch (err) {
        this.showToast(err.message, "error");
      }
    },

    async downloadModel(algorithm) {
      try {
        const url = `${API_BASE}/download/${this.currentSession.id}/${algorithm}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error("Download failed");
        const blob = await res.blob();
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${algorithm.replace(/\s+/g, "_").toLowerCase()}.pkl`;
        a.click();
        URL.revokeObjectURL(a.href);
        this.showToast("Model downloaded", "success");
      } catch (err) {
        this.showToast(err.message, "error");
      }
    },

    formatStat(val) {
      if (val === null || val === undefined) return "—";
      const n = Number(val);
      if (isNaN(n)) return val;
      if (Number.isInteger(n)) return n.toLocaleString();
      return n.toFixed(4);
    },

    showToast(message, type = "success") {
      this.toast = { message, type };
      setTimeout(() => (this.toast = null), 4000);
    },
  },

  mounted() {
    this.fetchSessions();
  },
});

app.mount("#app");
