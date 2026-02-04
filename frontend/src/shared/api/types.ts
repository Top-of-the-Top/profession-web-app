// src/shared/api/types.ts
export interface ApiCourse {
	course_id: string,
  title: string;
  price: number;
  image_url: string;
}

export interface ApiLandingResponse {
  number_of_courses: number;
  data: ApiCourse[];
}
