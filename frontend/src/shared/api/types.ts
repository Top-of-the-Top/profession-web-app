// src/shared/api/types.ts
export interface ApiCourse {
  name: string;
  price: number;
  image: string;
}

export interface ApiLandingResponse {
  number_of_courses: number;
  data: ApiCourse[];
}
