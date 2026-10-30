export const ROLES = {
  SUPER_ADMIN: 'SUPER_ADMIN',
  BUSINESS_OWNER: 'BUSINESS_OWNER',
  STAFF: 'STAFF',
  CUSTOMER: 'CUSTOMER',
};

export const MEMBER_ROLES = {
  OWNER: 'OWNER',
  MANAGER: 'MANAGER',
  STAFF: 'STAFF',
};

export const ROLE_LABELS = {
  SUPER_ADMIN: 'Super admin',
  BUSINESS_OWNER: 'Business owner',
  STAFF: 'Staff',
  CUSTOMER: 'Customer',
  OWNER: 'Owner',
  MANAGER: 'Manager',
};

export const HOME_PATH_BY_ROLE = {
  SUPER_ADMIN: '/admin',
  BUSINESS_OWNER: '/owner',
  STAFF: '/staff',
  CUSTOMER: '/customer',
};

export const BUSINESS_CATEGORIES = [
  { value: 'BANK', label: 'Bank' },
  { value: 'SALON', label: 'Salon' },
  { value: 'GOVERNMENT', label: 'Government office' },
  { value: 'REPAIR_CENTER', label: 'Repair center' },
  { value: 'SERVICE_CENTER', label: 'Service center' },
  { value: 'CLINIC', label: 'Clinic' },
  { value: 'CUSTOMER_SERVICE', label: 'Customer service' },
  { value: 'OTHER', label: 'Other' },
];

export const categoryLabel = (value) =>
  BUSINESS_CATEGORIES.find((category) => category.value === value)?.label ?? value;

export const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
