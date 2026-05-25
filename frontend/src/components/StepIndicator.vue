<template>
  <div class="step-indicator">
    <template v-for="(label, index) in stepLabels" :key="index">
      <span
        class="step-dot"
        :class="{
          'step-active': index + 1 === currentStep,
          'step-done': index + 1 < currentStep,
          'step-pending': index + 1 > currentStep,
        }"
      >
        <SvgIcon v-if="index + 1 < currentStep" name="check" :size="13" :stroke-width="3" />
        <template v-else>{{ index + 1 }}</template>
      </span>
      <span
        v-if="index < stepLabels.length - 1"
        class="step-line"
        :class="{ 'line-done': index + 1 < currentStep }"
      ></span>
    </template>
    <span class="step-label-text">{{ stepLabels[currentStep - 1] || '' }}</span>
  </div>
</template>

<script setup>
import SvgIcon from './ui/SvgIcon.vue'

defineProps({
  currentStep: { type: Number, default: 1 },
  totalSteps: { type: Number, default: 1 },
  stepLabels: { type: Array, default: () => [] },
})
</script>

<style scoped>
.step-indicator {
  display: flex;
  align-items: center;
  gap: 0;
}

.step-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
  flex-shrink: 0;
}

.step-active {
  background: var(--wf-accent);
  color: var(--wf-text-on-accent);
  box-shadow: 0 0 12px var(--wf-accent-glow);
}

.step-done {
  background: var(--wf-success);
  color: #000;
}

.step-pending {
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-muted);
  border: 1px solid var(--wf-border);
}

.step-line {
  width: 28px;
  height: 1px;
  background: var(--wf-border);
  margin: 0 4px;
  flex-shrink: 0;
}

.step-line.line-done {
  background: var(--wf-success);
}

.step-label-text {
  font-size: 13px;
  color: var(--wf-text-secondary);
  margin-left: var(--spacing-sm);
  font-family: var(--font-sans);
}
</style>
