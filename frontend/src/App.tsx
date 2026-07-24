import { Provider } from 'react-redux'
import { store } from './app/store'
import { ComplaintIntakePage } from './pages/ComplaintIntakePage'

function App() {
  return (
    <Provider store={store}>
      <ComplaintIntakePage />
    </Provider>
  )
}

export default App
