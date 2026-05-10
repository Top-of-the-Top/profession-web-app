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

export interface ApiUserResponse {
  first_name: string | null;
  last_name: string | null;
  phone_number: string | null;
  email: string | null;
  gender: string | null;
  birthday: string | null;
  avatar: string | null;
  assets: {
    user_avatar: Array<{
      asset_id: string;
      filename: string;
      mime_type: string;
      size_bytes: number;
      url: string;
    }>;
  };
}

