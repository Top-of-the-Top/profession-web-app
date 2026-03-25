import { landingApi } from '../../../shared/api/landingApi';
import { type ApiLandingResponse } from '../../../shared/api/types';
import { type Track } from '../../../schemas/types'

const TRACKS_COLOR_SCHEMES: Omit<Track, 'id' | 'title' | 'price' | 'image'>[] =
  [
    {
      bgColor: '#E5E7EB',
      accentColor: '#191970',
      titleColor: '#E5E7EB',
      subtitleColor: '#000000',
      arrowColor: '#E5E7EB',
      arrowBgColor: '#191A23',
      moreColor: '#000000',
    },
    {
      bgColor: '#191970',
      accentColor: '#F3F3F3',
      titleColor: '#000000',
      subtitleColor: '#E5E7EB',
      arrowColor: '#E5E7EB',
      arrowBgColor: '#191A23',
      moreColor: '#E5E7EB',
    },
    {
      bgColor: '#191A23',
      accentColor: '#F3F3F3',
      titleColor: '#000000',
      subtitleColor: '#E5E7EB',
      arrowColor: '#000000',
      arrowBgColor: '#FFFFFF',
      moreColor: '#ffffff',
    },
    {
      bgColor: '#E5E7EB',
      accentColor: '#191970',
      titleColor: '#E5E7EB',
      subtitleColor: '#000000',
      arrowColor: '#E5E7EB',
      arrowBgColor: '#191A23',
      moreColor: '#000000',
    },
    {
      bgColor: '#191970',
      accentColor: '#F3F3F3',
      titleColor: '#000000',
      subtitleColor: '#E5E7EB',
      arrowColor: '#E5E7EB',
      arrowBgColor: '#191A23',
      moreColor: '#E5E7EB',
    },
    {
      bgColor: '#191A23',
      accentColor: '#F3F3F3',
      titleColor: '#000000',
      subtitleColor: '#E5E7EB',
      arrowColor: '#000000',
      arrowBgColor: '#ffffff',
      moreColor: '#ffffff',
    },
  ];

function transformApiCourses(apiData: ApiLandingResponse): Track[] {
  return (apiData.data || []).filter(course => course != null).map((course, index) => {
    const colorScheme = TRACKS_COLOR_SCHEMES[index % TRACKS_COLOR_SCHEMES.length];
    
    const imageSrc = course.image_url || '';
    
    return {
      id: `course-${index}`,
      title: course.title || 'Без названия',
      price: course.price || 0,
      image: imageSrc,
      ...colorScheme,
    };
  });
}

export const internalLandingApi = {
  async getCourses(): Promise<{
    number_of_courses: number;
    data: Track[];
  }> {
    try {
      const apiData = await landingApi.getCourses();
      
      return {
        number_of_courses: apiData?.number_of_courses || 0,
        data: transformApiCourses(apiData || { data: [] }),
      };
    } catch (error) {
      console.error('Failed to fetch landing courses:', error);
      return getFallbackCourses();
    }
  },
};


function getFallbackCourses() {
  const fallbackTracks: Track[] = [
    {
      id: 'medicine',
      title: 'Медицина',
      price: 3900,
      image: 'landing/il0.png',
      bgColor: '#E5E7EB',
      accentColor: '#191970',
      titleColor: '#E5E7EB',
      subtitleColor: '#000000',
      arrowColor: '#E5E7EB',
      arrowBgColor: '#191A23',
      moreColor: '#000000',
    },
    {
      id: 'chemistry',
      title: 'Химия',
      price: 3900,
      image: 'landing/il1.png',
      bgColor: '#191970',
      accentColor: '#FFFFFF',
      titleColor: '#000000',
      subtitleColor: '#E5E7EB',
      arrowColor: '#E5E7EB',
      arrowBgColor: '#191A23',
      moreColor: '#E5E7EB',
    },
    {
      id: 'programming',
      title: 'Программирование',
      image: 'landing/il2.png',
      price: 3900,
      bgColor: '#191A23',
      accentColor: '#FFFFFF',
      titleColor: '#000000',
      subtitleColor: '#E5E7EB',
      arrowColor: '#000000',
      arrowBgColor: '#FFFFFF',
      moreColor: '#ffffff',
    },
    {
      id: 'biology',
      title: 'Биология',
      image: 'landing/il3.png',
      bgColor: '#E5E7EB',
      price: 3900,
      accentColor: '#191970',
      titleColor: '#E5E7EB',
      subtitleColor: '#000000',
      arrowColor: '#E5E7EB',
      arrowBgColor: '#191A23',
      moreColor: '#000000',
    },
    {
      id: 'creativity',
      title: 'Творчество',
      image: 'landing/il4.png',
      price: 3900,
      bgColor: '#191970',
      accentColor: '#FFFFFF',
      titleColor: '#000000',
      subtitleColor: '#E5E7EB',
      arrowColor: '#E5E7EB',
      arrowBgColor: '#191A23',
      moreColor: '#E5E7EB',
    },
    {
      id: 'designer',
      title: 'Дизайнер',
      image: 'landing/il5.png',
      price: 3900,
      bgColor: '#191A23',
      accentColor: '#E5E7EB',
      titleColor: '#000000',
      subtitleColor: '#E5E7EB',
      arrowColor: '#000000',
      arrowBgColor: '#ffffff',
      moreColor: '#ffffff',
    },
  ];

  return {
    number_of_courses: fallbackTracks.length,
    data: fallbackTracks,
  };
}
