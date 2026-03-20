export interface Money {
  /** Amount in smallest currency unit (e.g., kopecks for RUB) */
  amount: number;
  /** ISO 4217 3-letter currency code */
  currency: string;
}

export type ProductStatus = "DRAFT" | "ACTIVE" | "ARCHIVED" | "DELETED";

export interface Brand {
  id: string;
  name: string;
  slug: string;
  logoUrl: string | null;
  logoStatus: string;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
  fullSlug: string;
  level: number;
  sortOrder: number;
  parentId: string | null;
}

export interface CategoryTreeNode extends Category {
  children: CategoryTreeNode[];
}

export interface Product {
  id: string;
  slug: string;
  titleI18n: Record<string, string>;
  descriptionI18n: Record<string, string>;
  status: ProductStatus;
  brandId: string;
  primaryCategoryId: string;
  tags: string[];
  version: number;
  createdAt: string;
  updatedAt: string;
}

export interface SKU {
  id: string;
  productId: string;
  skuCode: string;
  price: Money;
  compareAtPrice: Money | null;
  isActive: boolean;
  version: number;
  variantAttributes: VariantAttribute[];
}

export interface VariantAttribute {
  attributeId: string;
  attributeValueId: string;
}

export interface Attribute {
  id: string;
  code: string;
  slug: string;
  nameI18n: Record<string, string>;
  dataType: string;
  uiType: string;
  isDictionary: boolean;
  isFilterable: boolean;
  isSearchable: boolean;
  isComparable: boolean;
}

export interface AttributeValue {
  id: string;
  attributeId: string;
  code: string;
  slug: string;
  valueI18n: Record<string, string>;
  sortOrder: number;
}

export interface AttributeGroup {
  id: string;
  code: string;
  nameI18n: Record<string, string>;
  sortOrder: number;
}
