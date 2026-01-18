import styles from './Content.module.css';
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
	Card,
	CardContent
} from '../../../components/ui';

export default function Content(): React.JSX.Element {
  return (
    <div className={styles.parent}>
      <div className={styles.div1}>
				<img src="man-standing.png" alt="" />
			</div>
      <div className={styles.div2}> </div>
      <div className={styles.div3}> 
				<Carousel style={{ width: '90%', margin: '0 auto' }}>
        <CarouselContent>
          {Array.from({ length: 5 }).map((_, index) => (
            <CarouselItem key={index}>
              <div style={{ padding: '4px' }}>
                <Card>
                  <CardContent
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      padding: '24px',
											height: '29vh'
                      // aspectRatio: 1,
                    }}
                  >
                    <span style={{ fontSize: '36px', fontWeight: '600' }}>
                      {index + 1}
                    </span>
                  </CardContent>
                </Card>
              </div>
            </CarouselItem>
          ))}
        </CarouselContent>
        <CarouselPrevious />
        <CarouselNext />
      </Carousel>
			</div>
      <div className={styles.div4}> </div>
    </div>
  );
}
