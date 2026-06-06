<template>
  <svg
    class="svg-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    :aria-hidden="decorative ? 'true' : undefined"
    :role="decorative ? undefined : 'img'"
  >
    <title v-if="!decorative && title">{{ title }}</title>

    <template v-if="name === 'arrow-right'">
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </template>
    <template v-else-if="name === 'arrow-left'">
      <path d="M19 12H5" />
      <path d="m11 6-6 6 6 6" />
    </template>
    <template v-else-if="name === 'chevron-down'">
      <path d="m6 9 6 6 6-6" />
    </template>
    <template v-else-if="name === 'chevron-up'">
      <path d="m18 15-6-6-6 6" />
    </template>
    <template v-else-if="name === 'chevron-right'">
      <path d="m9 18 6-6-6-6" />
    </template>
    <template v-else-if="name === 'chevron-left'">
      <path d="m15 18-6-6 6-6" />
    </template>
    <template v-else-if="name === 'close'">
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </template>
    <template v-else-if="name === 'check'">
      <path d="m5 12 4 4L19 6" />
    </template>
    <template v-else-if="name === 'plus'">
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </template>
    <template v-else-if="name === 'minus'">
      <path d="M5 12h14" />
    </template>
    <template v-else-if="name === 'search'">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.8-3.8" />
    </template>
    <template v-else-if="name === 'trash'">
      <path d="M3 6h18" />
      <path d="M8 6V4c0-1.1.9-2 2-2h4c1.1 0 2 .9 2 2v2" />
      <path d="M19 6v14c0 1.1-.9 2-2 2H7c-1.1 0-2-.9-2-2V6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </template>
    <template v-else-if="name === 'edit'">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </template>
    <template v-else-if="name === 'save'">
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z" />
      <path d="M17 21v-8H7v8" />
      <path d="M7 3v5h8" />
    </template>
    <template v-else-if="name === 'settings'">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5h.1a1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
    </template>
    <template v-else-if="name === 'tool' || name === 'wrench'">
      <path d="M14.7 6.3a4 4 0 0 0-5 5L3 18l3 3 6.7-6.7a4 4 0 0 0 5-5l-2.6 2.6-2.8-2.8Z" />
    </template>
    <template v-else-if="name === 'globe' || name === 'world'">
      <circle cx="12" cy="12" r="10" />
      <path d="M2 12h20" />
      <path d="M12 2a15.3 15.3 0 0 1 0 20" />
      <path d="M12 2a15.3 15.3 0 0 0 0 20" />
    </template>
    <template v-else-if="name === 'book'">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5Z" />
    </template>
    <template v-else-if="name === 'folder'">
      <path d="M3 6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" />
    </template>
    <template v-else-if="name === 'file'">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6" />
    </template>
    <template v-else-if="name === 'paperclip'">
      <path d="m21.4 11.6-8.5 8.5a6 6 0 0 1-8.5-8.5l9.2-9.2a4 4 0 1 1 5.7 5.7L10 17.4a2 2 0 1 1-2.8-2.8l8.5-8.5" />
    </template>
    <template v-else-if="name === 'fish'">
      <path d="M3 12s4-6 10-6c4.5 0 8 6 8 6s-3.5 6-8 6C7 18 3 12 3 12Z" />
      <path d="m3 12-2.5-3v6Z" />
      <circle cx="16" cy="10" r=".8" fill="currentColor" stroke="none" />
      <path d="M8 12c1.4-1.2 2.8-1.2 4 0" />
    </template>
    <template v-else-if="name === 'map'">
      <path d="m9 18-6 3V6l6-3 6 3 6-3v15l-6 3Z" />
      <path d="M9 3v15" />
      <path d="M15 6v15" />
    </template>
    <template v-else-if="name === 'clock'">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 6v6l4 2" />
    </template>
    <template v-else-if="name === 'dna'">
      <path d="M7 3c5 3 5 15 10 18" />
      <path d="M17 3C12 6 12 18 7 21" />
      <path d="M8.5 7h7" />
      <path d="M8.5 17h7" />
      <path d="M10 12h4" />
    </template>
    <template v-else-if="name === 'list'">
      <path d="M8 6h13" />
      <path d="M8 12h13" />
      <path d="M8 18h13" />
      <path d="M3 6h.01" />
      <path d="M3 12h.01" />
      <path d="M3 18h.01" />
    </template>
    <template v-else-if="name === 'swirl'">
      <path d="M12 3a9 9 0 1 1-8.2 12.7" />
      <path d="M12 7a5 5 0 1 1-4.6 7" />
      <path d="M12 11a1 1 0 1 1-1 1" />
    </template>
    <template v-else-if="name === 'maximize'">
      <path d="M8 3H5a2 2 0 0 0-2 2v3" />
      <path d="M16 3h3a2 2 0 0 1 2 2v3" />
      <path d="M8 21H5a2 2 0 0 1-2-2v-3" />
      <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
    </template>
    <template v-else-if="name === 'refresh'">
      <path d="M21 12a9 9 0 0 1-15.6 6" />
      <path d="M3 12a9 9 0 0 1 15.6-6" />
      <path d="M18 3v4h-4" />
      <path d="M6 21v-4h4" />
    </template>
    <template v-else-if="name === 'send'">
      <path d="M22 2 11 13" />
      <path d="m22 2-7 20-4-9-9-4 20-7z" />
    </template>
    <template v-else-if="name === 'undo'">
      <path d="M9 7 4 12l5 5" />
      <path d="M4 12h10a6 6 0 0 1 0 12" transform="translate(0 -5)" />
    </template>
    <template v-else-if="name === 'redo'">
      <path d="m15 7 5 5-5 5" />
      <path d="M20 12H10a6 6 0 0 0 0 12" transform="translate(0 -5)" />
    </template>
    <template v-else-if="name === 'grid'">
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </template>
    <template v-else-if="name === 'info'">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4" />
      <path d="M12 8h.01" />
    </template>
    <template v-else-if="name === 'timeline-node'">
      <path d="M4 12h16" />
      <circle cx="7" cy="12" r="2.4" />
      <circle cx="17" cy="12" r="2.4" />
      <path d="M12 7v10" />
    </template>
    <template v-else-if="name === 'box'">
      <path d="m21 8-9-5-9 5 9 5 9-5Z" />
      <path d="M3 8v8l9 5 9-5V8" />
      <path d="M12 13v8" />
    </template>
    <template v-else-if="name === 'user'">
      <path d="M20 21a8 8 0 0 0-16 0" />
      <circle cx="12" cy="7" r="4" />
    </template>
    <template v-else-if="name === 'building'">
      <path d="M4 21V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v16" />
      <path d="M9 21v-5h3v5" />
      <path d="M8 7h.01" />
      <path d="M13 7h.01" />
      <path d="M8 11h.01" />
      <path d="M13 11h.01" />
      <path d="M2 21h20" />
    </template>
    <template v-else-if="name === 'bolt'">
      <path d="m13 2-9 13h8l-1 7 9-13h-8Z" />
    </template>
    <template v-else-if="name === 'brain'">
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-5 .3 2.5 2.5 0 0 1-3-3.1A3 3 0 0 1 4 11a2.5 2.5 0 0 1 1-4.8A2.5 2.5 0 0 1 9.5 2Z" />
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 5 .3 2.5 2.5 0 0 0 3-3.1A3 3 0 0 0 20 11a2.5 2.5 0 0 0-1-4.8A2.5 2.5 0 0 0 14.5 2Z" />
    </template>
    <template v-else-if="name === 'radio-on'">
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="3" fill="currentColor" stroke="none" />
    </template>
    <template v-else-if="name === 'radio-off'">
      <circle cx="12" cy="12" r="8" />
    </template>
    <template v-else-if="name === 'checkbox-on'">
      <rect x="4" y="4" width="16" height="16" rx="4" />
      <path d="m8 12 3 3 5-6" />
    </template>
    <template v-else-if="name === 'checkbox-off'">
      <rect x="4" y="4" width="16" height="16" rx="4" />
    </template>
    <template v-else>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v4" />
      <path d="M12 16h.01" />
    </template>
  </svg>
</template>

<script setup>
defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  strokeWidth: { type: [Number, String], default: 2 },
  decorative: { type: Boolean, default: true },
  title: { type: String, default: '' },
})
</script>
