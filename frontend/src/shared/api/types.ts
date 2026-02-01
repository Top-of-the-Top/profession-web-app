// src/shared/api/types.ts
export interface ApiCourse {
  title: string;
  price: number;
  image: string;
}

export interface ApiLandingResponse {
  number_of_courses: number;
  data: ApiCourse[];
}
