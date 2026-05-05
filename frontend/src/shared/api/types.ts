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

// Профиль текущего пользователя, который возвращает бекенд
export interface ApiUserResponse {
  first_name: string | null;
  last_name: string | null;
  phone_number: string | null;
  email: string | null;
  gender: string | null;
  birthday: string | null;
  avatar: string | null;
  avatar_url?: string | null;
}

