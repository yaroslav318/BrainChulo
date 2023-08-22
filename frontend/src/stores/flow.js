import { defineStore } from 'pinia';
import internalService from '@/services/internal';

export const useFlowStore = defineStore('flow', {
  state: () => ({
    allFlows: [],
    currentFlow: null,
  }),
  actions: {
    async fetchFlows() {
      let response = await internalService.request('/flows', 'GET');
      let flows = response;

      if (flows.length < 1) {
        return await this.addFlow();
      }

      this.allFlows = flows.map((flow) => {
        return {
          id: flow.id,
          label: flow.name,
        };
      });

      return this.allFlows;
    },
    setCurrentFlow(newFlow) {
      this.currentFlow = this.allFlows.find((flow) => flow.id === newFlow.id);
    },
    async updateCurrentFlowName(newName) {
      await internalService.request(`/flows/${this.currentFlowId}`, 'PUT', { name: newName });
      await this.fetchFlows();
      this.setCurrentFlow(this.getCurrentFlow);
    },

    async addFlow() {
      const newFlow = await internalService.request('/flows', 'POST', { name: 'New Flow' });
      await this.fetchFlows();

      return newFlow;
    }
  },
  getters: {
    getFlows: (state) => state.allFlows,
    getCurrentFlow: (state) => state.currentFlow,
    currentFlowId: (state) => state.currentFlow?.id,
    currentFlowName: (state) => state.currentFlow?.label,
  }
});