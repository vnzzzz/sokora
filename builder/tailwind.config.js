module.exports = {
  content: [
    "/app/app/templates/**/*.html",
    "/app/app/static/js/**/*.js",
    "./app/templates/**/*.html", // ローカル開発用
    "./app/static/js/**/*.js"    // ローカル開発用
  ],
  purge: false, // パージを無効化
  safelist: [
    // daisyUIの基本コンポーネントクラスをセーフリストに追加
    'btn', 'btn-primary', 'btn-secondary', 'btn-accent', 'btn-info', 'btn-success', 'btn-warning', 'btn-error',
    'btn-ghost', 'btn-link', 'btn-outline', 'btn-active', 'btn-disabled', 'btn-circle', 'btn-sm', 'btn-square',
    'btn-group', 'btn-xs', 'btn-lg', 'btn-wide',
    
    'card', 'card-body', 'card-title', 'card-actions', 'card-compact', 'card-normal', 'card-side',
    
    'menu', 'menu-title', 'menu-dropdown', 'menu-item', 'menu-sm', 'menu-md', 'menu-lg', 'menu-horizontal', 'menu-vertical',
    
    'navbar', 'navbar-start', 'navbar-center', 'navbar-end', 'navbar-item',
    
    'footer', 'footer-title', 'footer-center',
    
    'form-control', 'label', 'input', 'textarea', 'select', 'checkbox', 'radio', 'toggle', 'input-group', 'input-bordered', 
    'input-primary', 'input-secondary', 'input-accent', 'input-info', 'input-success', 'input-warning', 'input-error',
    'select-bordered', 'file-input', 'file-input-bordered',
    
    'badge', 'badge-primary', 'badge-secondary', 'badge-accent', 'badge-ghost', 'badge-outline', 'badge-info', 'badge-success', 'badge-warning', 'badge-error',
    'badge-lg', 'badge-md', 'badge-sm', 'badge-xs',
    
    'alert', 'alert-info', 'alert-success', 'alert-warning', 'alert-error',
    
    'tab', 'tabs', 'tab-active', 'tab-bordered', 'tab-lifted', 'tabs-boxed',
    
    'swap', 'swap-rotate', 'swap-on', 'swap-off', 'swap-active', 'swap-flip',
    
    'tooltip', 'tooltip-open', 'tooltip-top', 'tooltip-bottom', 'tooltip-left', 'tooltip-right', 'tooltip-primary', 'tooltip-secondary', 'tooltip-accent',
    
    'collapse', 'collapse-title', 'collapse-content', 'collapse-arrow', 'collapse-plus', 'collapse-open',
    
    'indicator', 'indicator-item', 'indicator-center', 'indicator-bottom', 'indicator-start', 'indicator-end', 'indicator-top',
    
    'loading', 'loading-spinner', 'loading-dots', 'loading-ring', 'loading-ball', 'loading-bars', 'loading-infinity',
    
    'drawer', 'drawer-toggle', 'drawer-content', 'drawer-side', 'drawer-overlay', 'drawer-open', 'drawer-end',
    
    'modal', 'modal-box', 'modal-action', 'modal-open', 'modal-bottom', 'modal-middle', 'modal-top',
    
    'dropdown', 'dropdown-content', 'dropdown-end', 'dropdown-bottom', 'dropdown-top', 'dropdown-left', 'dropdown-right',
    'dropdown-hover', 'dropdown-open',
    
    'table', 'table-zebra', 'table-pin-rows', 'table-pin-cols', 'table-compact', 'table-normal',
    
    // レイアウト関連
    'container', 'flex', 'flex-col', 'flex-row', 'grid', 'grid-cols-1', 'grid-cols-2', 'grid-cols-3', 'grid-cols-4',
    'grid-cols-5', 'grid-cols-6', 'grid-cols-7', 'grid-cols-8', 'grid-cols-9', 'grid-cols-10', 'grid-cols-11', 'grid-cols-12',
    'md:grid-cols-1', 'md:grid-cols-2', 'md:grid-cols-3', 'md:grid-cols-4', 'md:grid-cols-5', 'md:grid-cols-6', 
    'md:grid-cols-7', 'md:grid-cols-8', 'md:grid-cols-9', 'md:grid-cols-10', 'md:grid-cols-11', 'md:grid-cols-12',
    'lg:grid-cols-1', 'lg:grid-cols-2', 'lg:grid-cols-3', 'lg:grid-cols-4', 'lg:grid-cols-5', 'lg:grid-cols-6',
    'lg:grid-cols-7', 'lg:grid-cols-8', 'lg:grid-cols-9', 'lg:grid-cols-10', 'lg:grid-cols-11', 'lg:grid-cols-12',
    'col-span-1', 'col-span-2', 'col-span-3', 'col-span-4', 'col-span-5', 'col-span-6',
    'col-span-7', 'col-span-8', 'col-span-9', 'col-span-10', 'col-span-11', 'col-span-12',
    'md:col-span-1', 'md:col-span-2', 'md:col-span-3', 'md:col-span-4', 'md:col-span-5', 'md:col-span-6',
    'md:col-span-7', 'md:col-span-8', 'md:col-span-9', 'md:col-span-10', 'md:col-span-11', 'md:col-span-12',
    'lg:col-span-1', 'lg:col-span-2', 'lg:col-span-3', 'lg:col-span-4', 'lg:col-span-5', 'lg:col-span-6',
    'lg:col-span-7', 'lg:col-span-8', 'lg:col-span-9', 'lg:col-span-10', 'lg:col-span-11', 'lg:col-span-12',
    'gap-1', 'gap-2', 'gap-3', 'gap-4', 'gap-5', 'gap-6', 'gap-8', 'gap-10', 'gap-12',
    'p-1', 'p-2', 'p-3', 'p-4', 'p-5', 'p-6', 'p-8', 'p-10', 'p-12',
    'px-1', 'px-2', 'px-3', 'px-4', 'px-5', 'px-6', 'px-8', 'px-10', 'px-12',
    'py-1', 'py-2', 'py-3', 'py-4', 'py-5', 'py-6', 'py-8', 'py-10', 'py-12',
    'pl-1', 'pl-2', 'pl-3', 'pl-4', 'pl-5', 'pl-6', 'pl-8', 'pl-10', 'pl-12',
    'pr-1', 'pr-2', 'pr-3', 'pr-4', 'pr-5', 'pr-6', 'pr-8', 'pr-10', 'pr-12',
    'pt-1', 'pt-2', 'pt-3', 'pt-4', 'pt-5', 'pt-6', 'pt-8', 'pt-10', 'pt-12',
    'pb-1', 'pb-2', 'pb-3', 'pb-4', 'pb-5', 'pb-6', 'pb-8', 'pb-10', 'pb-12',
    'm-1', 'm-2', 'm-3', 'm-4', 'm-5', 'm-6', 'm-8', 'm-10', 'm-12',
    'mx-1', 'mx-2', 'mx-3', 'mx-4', 'mx-5', 'mx-6', 'mx-8', 'mx-10', 'mx-12', 'mx-auto',
    'my-1', 'my-2', 'my-3', 'my-4', 'my-5', 'my-6', 'my-8', 'my-10', 'my-12', 'my-auto',
    'ml-1', 'ml-2', 'ml-3', 'ml-4', 'ml-5', 'ml-6', 'ml-8', 'ml-10', 'ml-12', 'ml-auto',
    'mr-1', 'mr-2', 'mr-3', 'mr-4', 'mr-5', 'mr-6', 'mr-8', 'mr-10', 'mr-12', 'mr-auto',
    'mt-1', 'mt-2', 'mt-3', 'mt-4', 'mt-5', 'mt-6', 'mt-8', 'mt-10', 'mt-12', 'mt-auto',
    'mb-1', 'mb-2', 'mb-3', 'mb-4', 'mb-5', 'mb-6', 'mb-8', 'mb-10', 'mb-12', 'mb-auto',
    
    // メディアクエリ
    'md:flex', 'lg:flex', 'xl:flex', '2xl:flex',
    'md:hidden', 'lg:hidden', 'xl:hidden', '2xl:hidden',
    'md:block', 'lg:block', 'xl:block', '2xl:block',
    'md:flex-row', 'lg:flex-row', 'xl:flex-row', '2xl:flex-row',
    'md:flex-col', 'lg:flex-col', 'xl:flex-col', '2xl:flex-col',
    
    // 位置・表示制御
    'relative', 'absolute', 'fixed', 'static', 'sticky',
    'top-0', 'right-0', 'bottom-0', 'left-0',
    'z-0', 'z-10', 'z-20', 'z-30', 'z-40', 'z-50', 'z-100',
    'hidden', 'block', 'inline', 'inline-block', 'flex', 'inline-flex', 'grid', 'inline-grid',
    'visible', 'invisible', 'opacity-0', 'opacity-25', 'opacity-50', 'opacity-70', 'opacity-75', 'opacity-90', 'opacity-100',
    
    // アイコンサイズ制御
    'w-1', 'w-2', 'w-3', 'w-4', 'w-5', 'w-6', 'w-8', 'w-10', 'w-12', 'w-16', 'w-20', 'w-24', 'w-32', 'w-40', 'w-48',
    'w-56', 'w-64', 'w-auto', 'w-full', 'w-screen', 'w-min', 'w-max', 'w-fit', 'w-1/7',
    'h-1', 'h-2', 'h-3', 'h-4', 'h-5', 'h-6', 'h-8', 'h-10', 'h-12', 'h-16', 'h-20', 'h-24', 'h-32', 'h-40', 'h-48',
    'h-56', 'h-64', 'h-auto', 'h-full', 'h-screen', 'h-min', 'h-max', 'h-fit',
    'min-w-0', 'min-w-full', 'min-w-min', 'min-w-max', 'min-w-fit',
    'min-h-0', 'min-h-full', 'min-h-screen', 'min-h-min', 'min-h-max', 'min-h-fit',
    'max-w-0', 'max-w-full', 'max-w-min', 'max-w-max', 'max-w-fit', 'max-w-none', 'max-w-xs', 'max-w-sm', 
    'max-w-md', 'max-w-lg', 'max-w-xl', 'max-w-2xl', 'max-w-3xl', 'max-w-4xl', 'max-w-5xl', 'max-w-6xl', 'max-w-7xl',
    'max-w-[700px]', 'max-w-[800px]', 'max-w-[900px]', 'max-w-[1000px]', 'max-w-[1100px]', 'max-w-[1200px]',
    'max-h-0', 'max-h-full', 'max-h-screen', 'max-h-min', 'max-h-max', 'max-h-fit',
    
    // スクロール関連
    'overflow-auto', 'overflow-hidden', 'overflow-clip', 'overflow-visible', 'overflow-scroll',
    'overflow-x-auto', 'overflow-y-auto', 'overflow-x-hidden', 'overflow-y-hidden',
    'overflow-x-clip', 'overflow-y-clip', 'overflow-x-visible', 'overflow-y-visible',
    'overflow-x-scroll', 'overflow-y-scroll', 
    'scrollbar', 'scrollbar-thin', 'scrollbar-auto', 'scrollbar-none',
    'max-h-[75vh]', 'max-h-[80vh]', 'max-h-[85vh]', 'max-h-[90vh]', 'max-h-[95vh]',
    
    // テーブル関連
    'table-auto', 'table-fixed', 'border-collapse', 'border-separate', 'table-layout-auto', 'table-layout-fixed',
    'align-top', 'align-middle', 'align-bottom', 'align-baseline', 'align-text-top', 'align-text-bottom',
    'sticky', 'left-0', 'right-0', 'top-0', 'bottom-0', 'z-10', 'z-20', 'z-30',
    'left-[50px]', 'min-w-[max-content]',
    'rounded-tl-lg', 'rounded-tr-lg', 'rounded-bl-lg', 'rounded-br-lg',
    'shrink-0',
    
    // ツールチップ関連
    'custom-tooltip', 'holiday-tooltip', 'tooltip-text', 'tooltip-container', 'tooltip-content',
    'data-tooltip', 'data-tooltip-position', 'data-tooltip-text',
    
    // Tailwind utilityクラスで動的に使用される可能性があるもの
    'bg-base-100', 'bg-base-200', 'bg-base-300', 'bg-base-content',
    'bg-primary', 'bg-primary-focus', 'bg-primary-content',
    'bg-secondary', 'bg-secondary-focus', 'bg-secondary-content',
    'bg-accent', 'bg-accent-focus', 'bg-accent-content',
    'bg-neutral', 'bg-neutral-focus', 'bg-neutral-content',
    'bg-info', 'bg-info-content', 'bg-success', 'bg-success-content',
    'bg-warning', 'bg-warning-content', 'bg-error', 'bg-error-content',
    'bg-base-100/80', 'bg-base-200/80', 'bg-base-300/80',
    'bg-opacity-10', 'bg-opacity-20', 'bg-opacity-30', 'bg-opacity-40', 'bg-opacity-50', 
    'bg-opacity-60', 'bg-opacity-70', 'bg-opacity-80', 'bg-opacity-90',
    'bg-red-900/10', 'bg-blue-900/10', 'dark:bg-red-300/10', 'dark:bg-blue-300/10',
    'hover:bg-base-300/30',
    
    'text-base-content', 'text-primary', 'text-secondary', 'text-accent', 'text-neutral',
    'text-info', 'text-success', 'text-warning', 'text-error',
    'text-xs', 'text-sm', 'text-base', 'text-lg', 'text-xl', 'text-2xl', 'text-3xl', 'text-4xl', 'text-5xl',
    'text-[11px]',
    'font-normal', 'font-medium', 'font-semibold', 'font-bold',
    'text-left', 'text-center', 'text-right', 'text-justify',
    'text-red-600', 'text-blue-600', 'dark:text-red-400', 'dark:text-blue-400',
    'text-base-content/70',
    
    'border', 'border-base-300', 'border-primary', 'border-secondary', 'border-accent',
    'border-info', 'border-success', 'border-warning', 'border-error',
    'border-t', 'border-r', 'border-b', 'border-l',
    'border-0', 'border-2', 'border-4', 'border-8',
    'rounded-none', 'rounded-sm', 'rounded', 'rounded-md', 'rounded-lg', 'rounded-xl', 'rounded-2xl', 'rounded-3xl', 'rounded-full',
    
    'hover:bg-base-300', 'hover:text-base-content', 'hover:shadow', 'hover:shadow-lg',
    'hover:bg-primary', 'hover:bg-secondary', 'hover:bg-accent', 'hover:bg-neutral',
    'hover:bg-info', 'hover:bg-success', 'hover:bg-warning', 'hover:bg-error',
    'hover:text-primary', 'hover:text-secondary', 'hover:text-accent', 'hover:text-neutral',
    
    'focus:outline-none', 'focus:ring', 'focus:ring-1', 'focus:ring-2', 'focus:ring-4',
    'focus:ring-primary', 'focus:ring-secondary', 'focus:ring-accent',
    'focus:ring-offset-2', 'focus:ring-offset-base-200',
    
    'shadow', 'shadow-sm', 'shadow-md', 'shadow-lg', 'shadow-xl', 'shadow-2xl', 'shadow-none',
    
    'whitespace-nowrap', 'whitespace-normal', 'whitespace-pre', 'whitespace-pre-line', 'whitespace-pre-wrap',
    'truncate', 'overflow-auto', 'overflow-hidden', 'overflow-visible', 'overflow-scroll', 'overflow-x-auto', 'overflow-y-auto',
    
    'animate-spin', 'animate-ping', 'animate-pulse', 'animate-bounce',
    
    'transition', 'transition-all', 'transition-colors', 'transition-opacity', 'transition-shadow', 'transition-transform',
    'duration-75', 'duration-100', 'duration-150', 'duration-200', 'duration-300', 'duration-500', 'duration-700', 'duration-1000',
    'ease-linear', 'ease-in', 'ease-out', 'ease-in-out',
    
    // サイドバー関連
    'min-w-[200px]', 'max-w-[200px]', 'w-16', 'min-h-screen', 'h-screen', 'transition-all', 'duration-300', 'ease-in-out',
    'justify-start', 'justify-center', 'justify-between', 'justify-around', 'justify-evenly', 'items-center', 'items-start', 'items-end',
    'gap-1', 'gap-2', 'gap-3', 'gap-4', 'gap-5', 'px-0', 'px-1', 'px-2', 'px-3', 'px-4', 'px-5',
    'transition-opacity', 'opacity-0', 'opacity-100', 'flex-shrink-0',
    'rotate-180', 'ml-[200px]', 'ml-16', 'max-w-[calc(100vw-200px-1.5rem)]', 'max-w-[calc(100vw-64px-1.5rem)]',
    'flex-1', 'flex-auto', 'flex-initial', 'flex-none', 'space-y-1', 'space-y-2', 'space-y-3', 'space-y-4', 'space-y-5',
    'space-x-1', 'space-x-2', 'space-x-3', 'space-x-4', 'space-x-5',
    
    // 勤怠表示用
    'bg-remote', 'bg-office', 'bg-business-trip', 'bg-vacation',
    'text-remote', 'text-office', 'text-business-trip', 'text-vacation',
    'attendance-cell', 'cursor-pointer',
    
    // カレンダー関連
    'holiday-cell', 'holiday-text', 'holiday-tooltip', 'today-highlight', 'selected-date', 'selected-column',
    'calendar-cell', 'current-month-display', 'calendar-area', 'calendar-metadata', 'detail-area',
    'min-width:max-content', 'table-layout:fixed', 'min-width:70px', 'width:70px',
    'width:50px', 'min-width:50px', 'max-width:50px', 'width:200px', 'min-width:200px', 'max-width:200px',
    
    // テーマ切り替え関連
    'theme-controller', 'data-theme', 'data-tip',
    'var(--btn-primary-bg)', 'var(--btn-primary-color)',
    'position:fixed', 'bottom:1.5rem', 'right:1.5rem',
    
    // グループ表示用
    'attendance-grid', 'attendance-groups', 'attendance-group',
    
    // モーダル関連
    'modal-container', 'htmx:beforeSwap', 'htmx:afterSwap', 'htmx:afterRequest', 'htmx:navigated',
    
    // Alpine.js用
    'x-data', 'x-show', 'x-cloak', 'x-bind:class', 'x-init', 'x-watch', 'alpine:init'
  ],
  theme: { 
    extend: {
      width: {
        '1/7': '14.285714%',
      }
    } 
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: [
      'light','dark','cupcake','corporate','winter','night'
    ],
    // すべてのDaisyUIコンポーネントを含める
    base: true,
    styled: true,
    utils: true,
    logs: false,
    rtl: false,
    prefix: "",
    darkTheme: "dark"
  }
};